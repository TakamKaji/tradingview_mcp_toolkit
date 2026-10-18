"""Persist and resolve application screening results."""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from tradingview_screening.common.config import definition_path
from tradingview_screening.common.errors import AppError, ConfigError

TOKYO = ZoneInfo("Asia/Tokyo")
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
_FILE = re.compile(r"(?P<name>[A-Za-z0-9][A-Za-z0-9_-]*)_(?P<time>\d{6})(?:_(?P<serial>\d+))?\.json\Z")
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")


def _reject_json_constant(_value: str) -> None:
    raise ValueError("Non-standard JSON constant")


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def _valid_name(name: str, root: Path) -> None:
    # Use the same flat-name and Windows device-name rules as definitions.
    definition_path(root / "screenings", name, project_root=root)


def _valid_fingerprint(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == {"version", "algorithm", "value"}
        and type(value["version"]) is int
        and value["version"] >= 1
        and isinstance(value["algorithm"], str)
        and bool(value["algorithm"])
        and isinstance(value["value"], str)
        and _DIGEST.fullmatch(value["value"]) is not None
    )


def _executed_at(
    payload: Any, *, name: str | None = None, validate_fingerprint: bool = True,
    validate_uniqueness: bool = True,
) -> datetime | None:
    if not isinstance(payload, dict):
        return None
    if set(payload) != {
        "schemaVersion", "status", "operation", "name", "executedAt", "source",
        "metadata", "results", "errors",
    }:
        return None
    try:
        json.dumps(payload, allow_nan=False)
    except (TypeError, ValueError):
        return None
    if type(payload.get("schemaVersion")) is not int or payload["schemaVersion"] != 1:
        return None
    status = payload.get("status")
    if not isinstance(status, str) or status not in {"success", "partial"}:
        return None
    if payload.get("operation") != "screening" or payload.get("source") != "tradingview_official_mcp":
        return None
    actual_name = payload.get("name")
    if not isinstance(actual_name, str) or (name is not None and actual_name != name):
        return None
    metadata = payload.get("metadata")
    results = payload.get("results")
    if not isinstance(metadata, dict) or not isinstance(results, list):
        return None
    errors = payload.get("errors")
    if not isinstance(errors, list) or any(
        not isinstance(item, dict)
        or not isinstance(item.get("code"), str)
        or not isinstance(item.get("message"), str)
        for item in errors
    ):
        return None
    if (status == "success" and errors) or (status == "partial" and (not errors or not results)):
        return None
    if any(
        not isinstance(row, dict)
        or not isinstance(row.get("symbol"), str)
        or not row["symbol"]
        or any(not isinstance(key, str) for key in row)
        for row in results
    ):
        return None
    if (
        type(metadata.get("requestedCount")) is not int
        or metadata["requestedCount"] < 1
        or type(metadata.get("returnedCount")) is not int
        or metadata["returnedCount"] != len(results)
        or metadata["returnedCount"] > metadata["requestedCount"]
        or type(metadata.get("partial")) is not bool
        or metadata["partial"] is not (status == "partial")
        or type(metadata.get("durationMs")) is not int
        or metadata["durationMs"] < 0
        or ("cacheHit" in metadata and type(metadata["cacheHit"]) is not bool)
    ):
        return None
    if (
        validate_fingerprint
        and "definitionFingerprint" in metadata
        and not _valid_fingerprint(metadata["definitionFingerprint"])
    ):
        return None
    coverage_fields = {"requestedLimit", "totalCount", "limitReached", "completeCoverage"}
    if coverage_fields.intersection(metadata) and (
        not coverage_fields.issubset(metadata)
        or type(metadata["requestedLimit"]) is not int
        or metadata["requestedLimit"] != metadata["requestedCount"]
        or type(metadata["totalCount"]) is not int
        or metadata["totalCount"] < metadata["returnedCount"]
        or type(metadata["limitReached"]) is not bool
        or metadata["limitReached"] is not (
            metadata["returnedCount"] >= metadata["requestedLimit"]
        )
        or type(metadata["completeCoverage"]) is not bool
        or (validate_uniqueness and metadata["completeCoverage"] is not (
            metadata["returnedCount"] == metadata["totalCount"]
            and len({row["symbol"] for row in results}) == metadata["totalCount"]
        ))
    ):
        return None
    try:
        executed = datetime.fromisoformat(payload["executedAt"])
    except (KeyError, TypeError, ValueError):
        return None
    if executed.tzinfo is None or executed.utcoffset() is None:
        return None
    try:
        executed.astimezone(TOKYO).astimezone(UTC)
    except (OverflowError, ValueError):
        return None
    return executed


def save_result(payload: dict[str, Any], project_root: Path) -> Path:
    """Write one complete result without replacing an existing run."""
    name = payload.get("name")
    if not isinstance(name, str):
        raise AppError("RESULT_WRITE_ERROR", "Screening result is invalid")
    try:
        _valid_name(name, project_root)
    except ConfigError as exc:
        raise AppError("RESULT_WRITE_ERROR", "Screening result is invalid") from exc
    executed = _executed_at(payload, name=name)
    if executed is None:
        raise AppError("RESULT_WRITE_ERROR", "Screening result is invalid")
    local = executed.astimezone(TOKYO)
    result_root = project_root / "results"
    if result_root.is_symlink() or not result_root.resolve().is_relative_to(project_root.resolve()):
        raise AppError("RESULT_WRITE_ERROR", "Cannot save screening result")
    folder = result_root / local.strftime("%Y-%m-%d")
    if folder.is_symlink() or not folder.resolve().is_relative_to(result_root.resolve()):
        raise AppError("RESULT_WRITE_ERROR", "Cannot save screening result")
    temporary: Path | None = None
    try:
        folder.mkdir(parents=True, exist_ok=True)
        body = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), allow_nan=False)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=folder, suffix=".tmp", delete=False) as temp:
            temporary = Path(temp.name)
            temp.write(body)
            temp.flush()
            os.fsync(temp.fileno())
        stem = f"{name}_{local:%H%M%S}"
        for serial in range(10000):
            candidate = folder / f"{stem}{'_' + str(serial) if serial else ''}.json"
            try:
                os.link(temporary, candidate)
            except FileExistsError:
                continue
            return candidate
        raise AppError("RESULT_WRITE_ERROR", "Cannot allocate result filename")
    except (OSError, TypeError, ValueError) as exc:
        raise AppError("RESULT_WRITE_ERROR", "Cannot save screening result") from exc
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                # The published hard link is complete; cleanup failure must not
                # turn a successful result into an execution failure.
                pass


@dataclass(frozen=True)
class _StoredResult:
    payload: dict[str, Any]
    path: Path
    executed: datetime
    serial: int


def _scan_results(
    project_root: Path, name: str | None, *, validate_fingerprint: bool = True,
    validate_uniqueness: bool = True,
) -> list[_StoredResult]:
    """Read safe, timestamp-matched snapshots in deterministic newest-first order."""
    if name is not None:
        _valid_name(name, project_root)
    root = project_root / "results"
    if root.is_symlink() or not root.resolve().is_relative_to(project_root.resolve()):
        raise AppError("RESULT_READ_ERROR", "Cannot read screening results")
    found: list[_StoredResult] = []
    try:
        folders = root.iterdir()
        for folder in folders:
            if (
                not folder.is_dir() or folder.is_symlink()
                or not folder.resolve().is_relative_to(root.resolve())
                or not _DATE.fullmatch(folder.name)
            ):
                continue
            for path in folder.iterdir():
                if (
                    not path.is_file() or path.is_symlink()
                    or not path.resolve().is_relative_to(folder.resolve())
                ):
                    continue
                match = _FILE.fullmatch(path.name)
                if match is None or (name is not None and match["name"] != name):
                    continue
                try:
                    payload = json.loads(
                        path.read_text(encoding="utf-8"),
                        parse_constant=_reject_json_constant,
                        object_pairs_hook=_unique_json_object,
                    )
                except (OSError, UnicodeError, ValueError):
                    continue
                executed = _executed_at(
                    payload, name=match["name"], validate_fingerprint=validate_fingerprint,
                    validate_uniqueness=validate_uniqueness,
                )
                if executed is None:
                    continue
                local = executed.astimezone(TOKYO)
                if folder.name != local.strftime("%Y-%m-%d") or match["time"] != local.strftime("%H%M%S"):
                    continue
                try:
                    serial = int(match["serial"] or 0)
                except ValueError:
                    continue
                found.append(_StoredResult(payload, path, executed, serial))
    except FileNotFoundError:
        pass
    except OSError as exc:
        raise AppError("RESULT_READ_ERROR", "Cannot read screening results") from exc
    found.sort(
        key=lambda item: (item.executed.astimezone(UTC), item.serial, item.path.name),
        reverse=True,
    )
    return found


def latest_result(project_root: Path, name: str | None = None) -> dict[str, Any]:
    """Find the newest validated application result across date folders."""
    found = _scan_results(project_root, name)
    if not found:
        raise AppError("RESULT_NOT_FOUND", "No screening result found")
    return found[0].payload


def history_result(project_root: Path, name: str, *, limit: int = 20) -> dict[str, Any]:
    """List successful local snapshots without contacting TradingView."""
    if type(limit) is not int or not 1 <= limit <= 1000:
        raise AppError("CLI_USAGE_ERROR", "Invalid history limit")
    items = []
    for item in _scan_results(project_root, name):
        if item.payload["status"] != "success":
            continue
        metadata = item.payload["metadata"]
        items.append({
            "file": item.path.relative_to(project_root).as_posix(),
            "executedAt": item.payload["executedAt"],
            "returnedCount": metadata["returnedCount"],
            "totalCount": metadata.get("totalCount"),
            "completeCoverage": metadata.get("completeCoverage"),
            "definitionFingerprint": metadata.get("definitionFingerprint"),
        })
        if len(items) == limit:
            break
    return {
        "schemaVersion": 1, "status": "success", "operation": "screening_history",
        "name": name, "items": items,
    }
