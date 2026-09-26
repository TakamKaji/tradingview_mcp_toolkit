"""Local ownership mapping and cross-process Watchlist synchronization locks."""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
import os
import re
import tempfile
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import partial
from pathlib import Path

from filelock import FileLock, Timeout
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    StrictStr,
    ValidationError,
    field_validator,
)

from tradingview_screening.common.config import definition_path
from tradingview_screening.common.errors import AppError

_SAFE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*\Z", re.ASCII)
_WINDOWS_RESERVED = {
    "CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


class ManagedWatchlist(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    watchlistId: StrictStr = Field(min_length=1)
    expectedName: StrictStr = Field(min_length=1, max_length=500)

    @field_validator("watchlistId", "expectedName")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Value must not be blank")
        return value

    @field_validator("watchlistId")
    @classmethod
    def decimal_id(cls, value: str) -> str:
        if re.fullmatch(r"[0-9]+", value, re.ASCII) is None:
            raise ValueError("Watchlist id must be decimal")
        return value


class ManagedWatchlistMapping(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    schemaVersion: StrictInt
    screenings: dict[str, ManagedWatchlist]

    @field_validator("schemaVersion")
    @classmethod
    def version_one(cls, value: int) -> int:
        if value != 1:
            raise ValueError("Unsupported mapping version")
        return value

    @field_validator("screenings")
    @classmethod
    def valid_screening_names(cls, value: dict[str, ManagedWatchlist]) -> dict[str, ManagedWatchlist]:
        for name in value:
            if not _valid_name(name):
                raise ValueError("Invalid screening name")
        return value


def _valid_name(name: str) -> bool:
    # Reuse the repository's flat definition-name and Windows reserved-name rules.
    return isinstance(name, str) and _SAFE_NAME.fullmatch(name) is not None and name.upper() not in _WINDOWS_RESERVED


def validate_screening_name(name: str, project_root: Path) -> None:
    definition_path(project_root / "screenings", name, project_root=project_root)


def _local_path(project_root: Path, *parts: str) -> Path:
    try:
        root = project_root.resolve()
        local = project_root / ".local"
        path = local.joinpath(*parts)
        if (
            local.is_symlink() or local.resolve() != root / ".local"
            or path.is_symlink() or path.resolve() != local.resolve().joinpath(*parts)
        ):
            raise AppError("WATCHLIST_LOCAL_PATH_ERROR", "Local Watchlist path is unsafe")
        return path
    except (OSError, RuntimeError) as exc:
        raise AppError("WATCHLIST_LOCAL_PATH_ERROR", "Local Watchlist path is unsafe") from exc


def _read_mapping(path: Path) -> ManagedWatchlistMapping:
    try:
        data = json.loads(path.read_text(encoding="utf-8"), parse_constant=_reject_constant)
        return ManagedWatchlistMapping.model_validate(data)
    except FileNotFoundError:
        return ManagedWatchlistMapping(schemaVersion=1, screenings={})
    except (OSError, UnicodeError, ValueError, ValidationError) as exc:
        raise AppError("WATCHLIST_MAPPING_INVALID", "Managed Watchlist mapping is invalid") from exc


def _reject_constant(_value: str) -> None:
    raise ValueError("Non-standard JSON constant")


def load_mapping(project_root: Path) -> ManagedWatchlistMapping:
    return _read_mapping(_local_path(project_root, "managed_watchlists.json"))


def _write_mapping(path: Path, mapping: ManagedWatchlistMapping) -> None:
    temporary: Path | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = mapping.model_dump_json(by_alias=True)
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=path.parent, suffix=".tmp", delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except OSError as exc:
        raise AppError("WATCHLIST_MAPPING_WRITE_ERROR", "Cannot save managed Watchlist mapping") from exc
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


def _lock_path(project_root: Path, category: str, value: str) -> Path:
    directory = _local_path(project_root, "watchlist_locks")
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise AppError("WATCHLIST_LOCK_ERROR", "Cannot prepare Watchlist lock") from exc
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return _local_path(project_root, "watchlist_locks", f"{category}-{digest}.lock")


@asynccontextmanager
async def watchlist_lock(
    project_root: Path, category: str, value: str, *, timeout: float = 10,
) -> AsyncIterator[None]:
    """Acquire filelock without blocking the event loop or leaking it on cancellation."""
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout < 0:
        raise AppError("WATCHLIST_LOCK_ERROR", "Invalid Watchlist lock timeout")
    path = _lock_path(project_root, category, value)
    lock = FileLock(path, thread_local=False)
    acquiring = asyncio.get_running_loop().run_in_executor(None, partial(lock.acquire, timeout=timeout))
    cancelled = False
    failure: BaseException | None = None
    while True:
        try:
            await asyncio.shield(acquiring)
            break
        except asyncio.CancelledError:
            # Keep the parent alive until the worker exits; asyncio.run may cancel
            # pending Tasks but does not cancel this shielded executor Future.
            cancelled = True
        except Exception as exc:  # noqa: BLE001 - filelock worker errors must become AppError.
            failure = exc
            break
    if cancelled:
        try:
            if lock.is_locked:
                lock.release()
        except Exception as exc:
            raise AppError("WATCHLIST_LOCK_ERROR", "Cannot release Watchlist lock") from exc
        raise asyncio.CancelledError
    if failure is not None:
        if isinstance(failure, Timeout):
            raise AppError("WATCHLIST_LOCK_TIMEOUT", "Watchlist lock timed out") from failure
        raise AppError("WATCHLIST_LOCK_ERROR", "Cannot acquire Watchlist lock") from failure
    try:
        yield
    finally:
        try:
            lock.release()
        except Exception as exc:
            raise AppError("WATCHLIST_LOCK_ERROR", "Cannot release Watchlist lock") from exc


async def store_managed_watchlist(
    project_root: Path, name: str, managed: ManagedWatchlist, *, timeout: float = 10,
) -> None:
    """Merge one ownership record under a brief global mapping lock."""
    if not _valid_name(name):
        raise AppError("WATCHLIST_MAPPING_INVALID", "Invalid managed screening name")
    try:
        managed = ManagedWatchlist.model_validate(managed.model_dump())
    except (AttributeError, ValidationError) as exc:
        raise AppError("WATCHLIST_MAPPING_INVALID", "Invalid managed Watchlist entry") from exc
    async with watchlist_lock(project_root, "mapping", "global", timeout=timeout):
        path = _local_path(project_root, "managed_watchlists.json")
        mapping = _read_mapping(path)
        mapping.screenings[name] = managed
        try:
            mapping = ManagedWatchlistMapping.model_validate(mapping.model_dump())
        except ValidationError as exc:
            raise AppError("WATCHLIST_MAPPING_INVALID", "Managed Watchlist mapping is invalid") from exc
        _write_mapping(path, mapping)
