"""Deterministic Screening to managed Watchlist synchronization."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tradingview_screening.common.errors import AppError, TransientRequestError
from tradingview_screening.integrations.tradingview.client import TradingViewClient
from tradingview_screening.integrations.tradingview.watchlist_normalization import (
    WatchlistSnapshot,
    add_managed_symbols,
    create_managed_watchlist,
    get_managed_watchlist,
    remove_managed_symbols,
    valid_watchlist_symbol,
)

from .managed_watchlists import (
    ManagedWatchlist,
    load_mapping,
    store_managed_watchlist,
    validate_screening_name,
    watchlist_lock,
)
from .results import _executed_at
from .schema import ScreeningDefinition


def desired_symbols(
    screening: ScreeningDefinition, normalized_result: dict[str, Any], project_root: Path,
) -> tuple[str, ...]:
    """Reject an unsafe result before any Watchlist Read or Write."""
    validate_screening_name(screening.name, project_root)
    if (
        not isinstance(normalized_result, dict)
        or normalized_result.get("status") != "success"
        or normalized_result.get("errors") != []
    ):
        raise AppError("WATCHLIST_RESULT_INVALID", "Screening result is not safe for Watchlist sync")
    rows = normalized_result.get("results")
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise AppError("WATCHLIST_RESULT_INVALID", "Screening result is not safe for Watchlist sync")
    symbols = [row.get("symbol") for row in rows]
    if any(not valid_watchlist_symbol(symbol) for symbol in symbols):
        raise AppError("WATCHLIST_SYMBOL_INVALID", "Screening result contains an invalid symbol")
    if _executed_at(normalized_result, name=screening.name) is None:
        raise AppError("WATCHLIST_RESULT_INVALID", "Screening result is not safe for Watchlist sync")
    return tuple(sorted(set(symbols)))


def symbol_diff(
    desired: tuple[str, ...], current: tuple[str, ...],
) -> tuple[tuple[str, ...], tuple[str, ...], int]:
    desired_set = set(desired)
    current_set = set(current)
    return (
        tuple(sorted(desired_set - current_set)),
        tuple(sorted(current_set - desired_set)),
        len(desired_set & current_set),
    )


def _safe_current(snapshot: WatchlistSnapshot) -> tuple[str, ...]:
    if any(not valid_watchlist_symbol(symbol) for symbol in snapshot.symbols):
        raise AppError("MCP_SCHEMA_MISMATCH", "Watchlist contains an invalid symbol")
    return tuple(sorted(set(snapshot.symbols)))


def _result(
    screening: ScreeningDefinition, *, status: str, snapshot: WatchlistSnapshot | None,
    created: bool, added: tuple[str, ...] = (), removed: tuple[str, ...] = (),
    unchanged_count: int = 0, error: AppError | None = None,
    skipped: bool = False,
) -> dict[str, Any]:
    payload = {
        "schemaVersion": 1,
        "status": status,
        "operation": "watchlist_sync",
        "screening": screening.name,
        "watchlistId": snapshot.watchlist_id if snapshot else None,
        "watchlistName": snapshot.name if snapshot else None,
        "created": created,
        "added": list(added),
        "removed": list(removed),
        "unchangedCount": unchanged_count,
        "skipped": skipped,
        "errors": [{"code": error.code, "message": error.message}] if error else [],
    }
    if skipped:
        payload["reason"] = "watchlist_disabled"
    return payload


def _safe_error(error: BaseException, *, write: bool) -> AppError:
    if isinstance(error, AppError):
        return error
    if isinstance(error, (TimeoutError, TransientRequestError, ConnectionResetError)):
        code = "WATCHLIST_WRITE_UNCONFIRMED" if write else "WATCHLIST_READ_ERROR"
        return AppError(code, "Watchlist operation could not be confirmed")
    return AppError("WATCHLIST_OPERATION_ERROR", "Watchlist operation failed")


async def _create_and_store(
    screening: ScreeningDefinition, client: TradingViewClient, project_root: Path,
    *, lock_timeout: float,
) -> WatchlistSnapshot:
    name = screening.watchlist.name  # type: ignore[union-attr]  # enabled validated by caller
    if name is None or len(name) > 500:
        raise AppError("WATCHLIST_NAME_INVALID", "Watchlist name is invalid")
    try:
        snapshot = await create_managed_watchlist(client, name)
    except (AppError, TimeoutError, TransientRequestError, ConnectionResetError) as exc:
        if isinstance(exc, AppError):
            raise
        raise _safe_error(exc, write=True) from exc
    try:
        await store_managed_watchlist(
            project_root, screening.name,
            ManagedWatchlist(watchlistId=snapshot.watchlist_id, expectedName=name),
            timeout=lock_timeout,
        )
    except AppError as exc:
        raise AppError(
            "WATCHLIST_MAPPING_WRITE_ERROR",
            f"Watchlist {snapshot.watchlist_id} was created, but ownership mapping was not saved",
        ) from exc
    return snapshot


async def _sync_existing(
    screening: ScreeningDefinition, client: TradingViewClient,
    desired: tuple[str, ...], snapshot: WatchlistSnapshot, *, created: bool,
) -> dict[str, Any]:
    current = _safe_current(snapshot)
    to_add, to_remove, unchanged = symbol_diff(desired, current)
    if not to_add and not to_remove:
        return _result(
            screening, status="success", snapshot=snapshot, created=created,
            unchanged_count=unchanged,
        )
    added: tuple[str, ...] = ()
    if to_add:
        try:
            await add_managed_symbols(client, snapshot.watchlist_id, to_add)
            after_add = await get_managed_watchlist(client, snapshot.watchlist_id)
            if set(_safe_current(after_add)) != set(current) | set(to_add):
                raise AppError("WATCHLIST_STATE_UNCONFIRMED", "Watchlist add result could not be confirmed")
            added = to_add
        except (AppError, TimeoutError, TransientRequestError, ConnectionResetError) as exc:
            return _result(
                screening, status="failed", snapshot=snapshot, created=created,
                unchanged_count=unchanged, error=_safe_error(exc, write=True),
            )
    if to_remove:
        try:
            await remove_managed_symbols(client, snapshot.watchlist_id, to_remove)
            after_remove = await get_managed_watchlist(client, snapshot.watchlist_id)
            expected = (set(current) | set(added)) - set(to_remove)
            if set(_safe_current(after_remove)) != expected:
                raise AppError("WATCHLIST_STATE_UNCONFIRMED", "Watchlist remove result could not be confirmed")
        except (AppError, TimeoutError, TransientRequestError, ConnectionResetError) as exc:
            return _result(
                screening, status="partial" if added else "failed", snapshot=snapshot,
                created=created, added=added, unchanged_count=unchanged,
                error=_safe_error(exc, write=True),
            )
    return _result(
        screening, status="success", snapshot=snapshot, created=created,
        added=added, removed=to_remove, unchanged_count=unchanged,
    )


async def sync_screening_watchlist(
    screening: ScreeningDefinition, normalized_result: dict[str, Any],
    client: TradingViewClient, project_root: Path, *, lock_timeout: float = 10,
) -> dict[str, Any]:
    """Sync one successful Phase 6 result to its app-owned TradingView Watchlist."""
    if screening.watchlist is None or not screening.watchlist.enabled:
        return _result(screening, status="success", snapshot=None, created=False, skipped=True)
    desired = desired_symbols(screening, normalized_result, project_root)
    async with watchlist_lock(project_root, "owner", screening.name, timeout=lock_timeout):
        mapped = load_mapping(project_root).screenings.get(screening.name)
        created = False
        if mapped is None:
            snapshot = await _create_and_store(
                screening, client, project_root, lock_timeout=lock_timeout,
            )
            created = True
        else:
            async with watchlist_lock(
                project_root, "id", mapped.watchlistId, timeout=lock_timeout,
            ):
                try:
                    snapshot = await get_managed_watchlist(client, mapped.watchlistId)
                except (AppError, TimeoutError, TransientRequestError, ConnectionResetError) as exc:
                    if not isinstance(exc, AppError) or exc.code != "WATCHLIST_NOT_FOUND":
                        if isinstance(exc, AppError):
                            raise
                        raise _safe_error(exc, write=False) from exc
                else:
                    return await _sync_existing(
                        screening, client, desired, snapshot, created=False,
                    )
            # Only a positively classified not-found condition permits recreation.
            snapshot = await _create_and_store(
                screening, client, project_root, lock_timeout=lock_timeout,
            )
            created = True
        async with watchlist_lock(
            project_root, "id", snapshot.watchlist_id, timeout=lock_timeout,
        ):
            try:
                current = await get_managed_watchlist(client, snapshot.watchlist_id)
            except (AppError, TimeoutError, TransientRequestError, ConnectionResetError) as exc:
                if isinstance(exc, AppError):
                    raise
                raise _safe_error(exc, write=False) from exc
            return await _sync_existing(
                screening, client, desired, current, created=created,
            )
