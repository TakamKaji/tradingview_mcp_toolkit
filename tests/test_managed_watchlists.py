from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from filelock import FileLock
from pydantic import ValidationError

from tradingview_screening.common.errors import AppError
from tradingview_screening.screening.managed_watchlists import (
    ManagedWatchlist,
    ManagedWatchlistMapping,
    load_mapping,
    store_managed_watchlist,
    watchlist_lock,
)
from tradingview_screening.screening.validators import validate_screening
from tradingview_screening.screening.watchlist_sync import desired_symbols, symbol_diff


def screening() -> dict:
    return {
        "schemaVersion": 1,
        "name": "sample",
        "market": "japan",
        "symbolTypes": ["stock"],
        "limit": 10,
        "columns": ["name"],
        "watchlist": {"enabled": True, "name": "[Auto] Sample"},
    }


def result(symbols: list[str], *, status: str = "success") -> dict:
    return {
        "schemaVersion": 1,
        "status": status,
        "operation": "screening",
        "name": "sample",
        "executedAt": "2026-09-26T12:00:00+09:00",
        "source": "tradingview_official_mcp",
        "metadata": {
            "requestedCount": 10,
            "returnedCount": len(symbols),
            "partial": status == "partial",
            "durationMs": 12,
        },
        "results": [{"symbol": symbol} for symbol in symbols],
        "errors": [] if status == "success" else [{"code": "X", "message": "partial"}],
    }


def test_watchlist_symbols_accept_legacy_and_new_top_n_metadata(tmp_path: Path) -> None:
    payload = result(["TSE:7203"])
    screening_definition = validate_screening(screening())
    assert desired_symbols(screening_definition, payload, tmp_path) == ("TSE:7203",)
    payload["metadata"].update({
        "requestedLimit": 10, "totalCount": 100,
        "limitReached": False, "completeCoverage": False,
    })
    assert desired_symbols(screening_definition, payload, tmp_path) == ("TSE:7203",)


def test_mapping_first_create_and_load(tmp_path: Path) -> None:
    assert load_mapping(tmp_path).screenings == {}
    managed = ManagedWatchlist(watchlistId="123", expectedName="[Auto] Sample")
    asyncio.run(store_managed_watchlist(tmp_path, "sample", managed))
    path = tmp_path / ".local" / "managed_watchlists.json"
    assert json.loads(path.read_text(encoding="utf-8")) == {
        "schemaVersion": 1,
        "screenings": {"sample": {"watchlistId": "123", "expectedName": "[Auto] Sample"}},
    }
    assert load_mapping(tmp_path).screenings["sample"] == managed
    assert not list(path.parent.glob("*.tmp"))


@pytest.mark.parametrize("payload", [
    {"schemaVersion": 2, "screenings": {}},
    {"schemaVersion": True, "screenings": {}},
    {"schemaVersion": 1, "screenings": {}, "unknown": 1},
    {"schemaVersion": 1, "screenings": {"sample": {"watchlistId": "123"}}},
    {"schemaVersion": 1, "screenings": {"sample": {
        "watchlistId": "123", "expectedName": "X", "extra": 1,
    }}},
    {"schemaVersion": 1, "screenings": {"../escape": {
        "watchlistId": "123", "expectedName": "X",
    }}},
    {"schemaVersion": 1, "screenings": {"sample": {
        "watchlistId": "not numeric", "expectedName": "X",
    }}},
])
def test_mapping_schema_is_strict(payload: dict) -> None:
    with pytest.raises(ValidationError):
        ManagedWatchlistMapping.model_validate(payload)


def test_mapping_corrupt_json_is_error(tmp_path: Path) -> None:
    local = tmp_path / ".local"
    local.mkdir()
    (local / "managed_watchlists.json").write_text("{broken", encoding="utf-8")
    with pytest.raises(AppError) as caught:
        load_mapping(tmp_path)
    assert caught.value.code == "WATCHLIST_MAPPING_INVALID"


def test_mapping_write_fsync_failure_keeps_old_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = ManagedWatchlist(watchlistId="123", expectedName="First")
    asyncio.run(store_managed_watchlist(tmp_path, "sample", first))
    from tradingview_screening.screening import managed_watchlists as module

    def fail_fsync(_descriptor: int) -> None:
        raise OSError("fsync failed")

    monkeypatch.setattr(module.os, "fsync", fail_fsync)
    with pytest.raises(AppError) as caught:
        asyncio.run(store_managed_watchlist(
            tmp_path, "sample", ManagedWatchlist(watchlistId="456", expectedName="Second"),
        ))
    assert caught.value.code == "WATCHLIST_MAPPING_WRITE_ERROR"
    assert load_mapping(tmp_path).screenings["sample"] == first
    assert not list((tmp_path / ".local").glob("*.tmp"))


def test_mapping_global_lock_prevents_lost_updates(tmp_path: Path) -> None:
    async def update() -> None:
        await asyncio.gather(
            store_managed_watchlist(
                tmp_path, "first", ManagedWatchlist(watchlistId="123", expectedName="First"),
            ),
            store_managed_watchlist(
                tmp_path, "second", ManagedWatchlist(watchlistId="456", expectedName="Second"),
            ),
        )

    asyncio.run(update())
    assert set(load_mapping(tmp_path).screenings) == {"first", "second"}


def test_lock_timeout_is_explicit(tmp_path: Path) -> None:
    async def hold() -> None:
        async with watchlist_lock(tmp_path, "id", "123"):
            with pytest.raises(AppError) as caught:
                async with watchlist_lock(tmp_path, "id", "123", timeout=0.01):
                    pytest.fail("same ID lock unexpectedly acquired")
            assert caught.value.code == "WATCHLIST_LOCK_TIMEOUT"

    asyncio.run(hold())


def test_twice_cancelled_waiter_does_not_leak_lock(tmp_path: Path) -> None:
    async def exercise() -> None:
        async with watchlist_lock(tmp_path, "id", "123"):
            async def waiter() -> None:
                async with watchlist_lock(tmp_path, "id", "123", timeout=1):
                    pytest.fail("cancelled waiter entered critical section")

            task = asyncio.create_task(waiter())
            await asyncio.sleep(0.02)
            task.cancel()
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        async with watchlist_lock(tmp_path, "id", "123", timeout=1):
            pass

    asyncio.run(exercise())


def test_cancelled_acquire_finishes_before_event_loop_shutdown(tmp_path: Path) -> None:
    from tradingview_screening.screening.managed_watchlists import _lock_path

    path = _lock_path(tmp_path, "id", "123")
    held = FileLock(path, thread_local=False)
    held.acquire()

    async def first_loop() -> None:
        async def waiter() -> None:
            async with watchlist_lock(tmp_path, "id", "123", timeout=1):
                pytest.fail("cancelled waiter entered critical section")

        task = asyncio.create_task(waiter())
        await asyncio.sleep(0.02)
        task.cancel()
        task.cancel()
        asyncio.get_running_loop().call_later(0.05, held.release)
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(first_loop())

    async def second_loop() -> None:
        async with watchlist_lock(tmp_path, "id", "123", timeout=0.2):
            pass

    asyncio.run(second_loop())


@pytest.mark.parametrize("timeout", [-1, float("nan"), float("inf"), True])
def test_invalid_lock_timeout_rejected(tmp_path: Path, timeout: float) -> None:
    async def exercise() -> None:
        async with watchlist_lock(tmp_path, "id", "123", timeout=timeout):
            pytest.fail("invalid timeout accepted")

    with pytest.raises(AppError) as caught:
        asyncio.run(exercise())
    assert caught.value.code == "WATCHLIST_LOCK_ERROR"


def test_local_mapping_path_escape_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    local = tmp_path / ".local"
    outside = tmp_path.parent / "outside"
    original_resolve = Path.resolve

    def outside_local(path: Path, *args: object, **kwargs: object) -> Path:
        return outside if path == local else original_resolve(path, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", outside_local)
    with pytest.raises(AppError) as caught:
        load_mapping(tmp_path)
    assert caught.value.code == "WATCHLIST_LOCAL_PATH_ERROR"


def test_internal_junction_like_redirect_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    local = tmp_path / ".local"
    redirected = tmp_path / "other_local"
    original_resolve = Path.resolve

    def redirect(path: Path, *args: object, **kwargs: object) -> Path:
        return redirected if path == local else original_resolve(path, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", redirect)
    with pytest.raises(AppError) as caught:
        load_mapping(tmp_path)
    assert caught.value.code == "WATCHLIST_LOCAL_PATH_ERROR"


def test_mapping_store_revalidates_mutated_entry(tmp_path: Path) -> None:
    managed = ManagedWatchlist(watchlistId="123", expectedName="Managed")
    managed.watchlistId = "invalid id"
    with pytest.raises(AppError) as caught:
        asyncio.run(store_managed_watchlist(tmp_path, "sample", managed))
    assert caught.value.code == "WATCHLIST_MAPPING_INVALID"
    assert not (tmp_path / ".local").exists()


def test_desired_symbols_and_diff_are_deterministic(tmp_path: Path) -> None:
    model = validate_screening(screening())
    assert desired_symbols(model, result(["TSE:7203", "TSE:6758", "TSE:7203"]), tmp_path) == (
        "TSE:6758", "TSE:7203",
    )
    assert desired_symbols(model, result([]), tmp_path) == ()
    assert symbol_diff(("TSE:6758", "TSE:7203"), ("TSE:7203", "TSE:9432")) == (
        ("TSE:6758",), ("TSE:9432",), 1,
    )
    assert symbol_diff(("TSE:7203", "TSE:6758"), ("TSE:6758", "TSE:7203")) == (
        (), (), 2,
    )


@pytest.mark.parametrize("symbols", [
    [""], [" "], ["TSE:"], [":7203"], ["TSE:7203 "] , ["TSE:72 03"],
    ["TSE:7203:EXTRA"],
])
def test_desired_symbols_rejects_invalid_values(tmp_path: Path, symbols: list[str]) -> None:
    with pytest.raises(AppError) as caught:
        desired_symbols(validate_screening(screening()), result(symbols), tmp_path)
    assert caught.value.code == "WATCHLIST_SYMBOL_INVALID"


@pytest.mark.parametrize("mutation", [
    {"status": "failed"},
    {"status": "partial", "errors": [{"code": "X", "message": "partial"}]},
    {"name": "other"},
    {"metadata": {"requestedCount": 10, "returnedCount": 2, "partial": False, "durationMs": 1}},
    {"errors": [{"code": "X", "message": "error"}]},
])
def test_desired_symbols_rejects_non_success_envelope(
    tmp_path: Path, mutation: dict,
) -> None:
    payload = result(["TSE:7203"])
    payload.update(mutation)
    with pytest.raises(AppError) as caught:
        desired_symbols(validate_screening(screening()), payload, tmp_path)
    assert caught.value.code == "WATCHLIST_RESULT_INVALID"
