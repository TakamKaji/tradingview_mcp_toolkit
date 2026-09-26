from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from tradingview_screening.common.errors import AppError
from tradingview_screening.common.request_governor import RequestGovernor
from tradingview_screening.integrations.tradingview.client import (
    ToolCatalog,
    ToolInfo,
    TradingViewClient,
)
from tradingview_screening.integrations.tradingview.schemas import TypedToolResponse
from tradingview_screening.integrations.tradingview.watchlist_normalization import (
    normalize_watchlist,
    normalize_watchlist_mutation,
)
from tradingview_screening.screening.managed_watchlists import (
    ManagedWatchlist,
    load_mapping,
    store_managed_watchlist,
)
from tradingview_screening.screening.validators import validate_screening
from tradingview_screening.screening.watchlist_sync import sync_screening_watchlist


def screening(name: str = "sample", *, enabled: bool = True):
    return validate_screening({
        "schemaVersion": 1, "name": name, "market": "japan",
        "symbolTypes": ["stock"], "limit": 10, "columns": ["name"],
        "watchlist": {"enabled": enabled, "name": "[Auto] Same Name"},
    })


def result(name: str = "sample", symbols: list[str] | None = None) -> dict:
    symbols = symbols if symbols is not None else ["TSE:7203"]
    return {
        "schemaVersion": 1, "status": "success", "operation": "screening",
        "name": name, "executedAt": "2026-09-26T12:00:00+09:00",
        "source": "tradingview_official_mcp",
        "metadata": {
            "requestedCount": 10, "returnedCount": len(symbols),
            "partial": False, "durationMs": 1,
        },
        "results": [{"symbol": symbol} for symbol in symbols], "errors": [],
    }


def response(data: dict | None, *, content: str = "sensitive raw provider content") -> TypedToolResponse:
    return TypedToolResponse.model_validate({
        "structured_content": data,
        "content": [{"type": "text", "text": content}],
    })


class FakeClient:
    def __init__(self) -> None:
        self.watchlists: dict[str, list[str]] = {}
        self.names: dict[str, str] = {}
        self.next_id = 100
        self.calls: list[tuple[str, str, tuple[str, ...]]] = []
        self.fail_action: str | None = None
        self.fail_after_apply = False
        self.get_delay = 0.0
        self.get_call_count = 0
        self.fail_get_on_call: int | None = None
        self.active_gets = 0
        self.max_active_gets = 0

    async def create_watchlist(self, request: Any) -> TypedToolResponse:
        self.calls.append(("create", request.name, tuple(request.symbols or ())))
        if self.fail_action == "create":
            raise TimeoutError("possibly created")
        identifier = str(self.next_id)
        self.next_id += 1
        self.watchlists[identifier] = []
        self.names[identifier] = request.name
        return self.snapshot(identifier)

    async def get_watchlist(self, request: Any) -> TypedToolResponse:
        identifier = request.watchlist_id
        self.calls.append(("get", identifier, ()))
        self.get_call_count += 1
        self.active_gets += 1
        self.max_active_gets = max(self.max_active_gets, self.active_gets)
        try:
            if self.get_delay:
                await asyncio.sleep(self.get_delay)
            if self.fail_action == "get" or self.fail_get_on_call == self.get_call_count:
                raise AppError("MCP_TOOL_ERROR", "MCP tool returned an error")
            if identifier not in self.watchlists:
                raise AppError("MCP_TOOL_ERROR", "MCP tool returned an error")
            return self.snapshot(identifier)
        finally:
            self.active_gets -= 1

    async def add_to_watchlist(self, request: Any) -> TypedToolResponse:
        identifier = request.watchlist_id
        self.calls.append(("add", identifier, tuple(request.symbols)))
        if self.fail_action == "add" and not self.fail_after_apply:
            raise TimeoutError("possibly added")
        for symbol in request.symbols:
            if symbol not in self.watchlists[identifier]:
                self.watchlists[identifier].append(symbol)
        if self.fail_action == "add":
            raise TimeoutError("possibly added")
        return response({"watchlist_id": identifier, "symbols": self.watchlists[identifier]})

    async def remove_from_watchlist(self, request: Any) -> TypedToolResponse:
        identifier = request.watchlist_id
        self.calls.append(("remove", identifier, tuple(request.symbols)))
        if self.fail_action == "remove":
            raise AppError("MCP_TOOL_ERROR", "MCP tool returned an error")
        self.watchlists[identifier] = [
            symbol for symbol in self.watchlists[identifier] if symbol not in request.symbols
        ]
        return response({"watchlist_id": identifier, "symbols": self.watchlists[identifier]})

    def snapshot(self, identifier: str) -> TypedToolResponse:
        return response({"watchlist": {
            "id": int(identifier), "name": self.names[identifier],
            "symbols": self.watchlists[identifier],
        }})

    async def list_watchlists(self, _request: Any) -> None:
        pytest.fail("list_watchlists must not be called")

    async def get_active_watchlist(self, _request: Any) -> None:
        pytest.fail("get_active_watchlist must not be called")

    async def delete_watchlist(self, _request: Any) -> None:
        pytest.fail("delete_watchlist must not be called")

    async def update_watchlist(self, _request: Any) -> None:
        pytest.fail("update_watchlist must not be called")


async def map_id(root: Path, name: str, identifier: str, expected_name: str = "Old Name") -> None:
    await store_managed_watchlist(
        root, name, ManagedWatchlist(watchlistId=identifier, expectedName=expected_name),
    )


def test_disabled_watchlist_skips_all_provider_and_filesystem(tmp_path: Path) -> None:
    client = FakeClient()
    output = asyncio.run(sync_screening_watchlist(screening(enabled=False), {}, client, tmp_path))
    assert output["status"] == "success"
    assert output["skipped"] is True
    assert output["reason"] == "watchlist_disabled"
    assert client.calls == []
    assert not (tmp_path / ".local").exists()


def test_missing_mapping_creates_new_even_with_same_name_present(tmp_path: Path) -> None:
    client = FakeClient()
    client.watchlists["7"] = ["TSE:6758"]
    client.names["7"] = "[Auto] Same Name"
    output = asyncio.run(sync_screening_watchlist(screening(), result(), client, tmp_path))
    assert output["status"] == "success"
    assert output["created"] is True
    assert output["watchlistId"] == "100"
    assert output["added"] == ["TSE:7203"]
    assert client.watchlists["7"] == ["TSE:6758"]
    assert load_mapping(tmp_path).screenings["sample"].watchlistId == "100"
    assert "sensitive" not in json.dumps(output)
    assert [call[0] for call in client.calls] == ["create", "get", "add", "get"]


def test_existing_id_diff_add_remove_and_expected_name_is_only_diagnostic(tmp_path: Path) -> None:
    client = FakeClient()
    client.watchlists["42"] = ["TSE:6758", "TSE:7203"]
    client.names["42"] = "Renamed by user"
    asyncio.run(map_id(tmp_path, "sample", "42", "Obsolete expected name"))
    output = asyncio.run(sync_screening_watchlist(
        screening(), result(symbols=["TSE:7203", "TSE:9432", "TSE:9432"]),
        client, tmp_path,
    ))
    assert output == {
        "schemaVersion": 1, "status": "success", "operation": "watchlist_sync",
        "screening": "sample", "watchlistId": "42", "watchlistName": "Renamed by user",
        "created": False, "added": ["TSE:9432"], "removed": ["TSE:6758"],
        "unchangedCount": 1, "skipped": False, "errors": [],
    }
    assert client.watchlists["42"] == ["TSE:7203", "TSE:9432"]
    assert [call[0] for call in client.calls] == ["get", "add", "get", "remove", "get"]
    assert load_mapping(tmp_path).screenings["sample"].watchlistId == "42"


def test_order_only_diff_is_noop_and_empty_desired_removes_all(tmp_path: Path) -> None:
    client = FakeClient()
    client.watchlists["42"] = ["TSE:9432", "TSE:7203"]
    client.names["42"] = "Managed"
    asyncio.run(map_id(tmp_path, "sample", "42"))
    noop = asyncio.run(sync_screening_watchlist(
        screening(), result(symbols=["TSE:7203", "TSE:9432"]), client, tmp_path,
    ))
    assert noop["status"] == "success" and noop["added"] == noop["removed"] == []
    assert [call[0] for call in client.calls] == ["get"]
    client.calls.clear()
    emptied = asyncio.run(sync_screening_watchlist(screening(), result(symbols=[]), client, tmp_path))
    assert emptied["removed"] == ["TSE:7203", "TSE:9432"]
    assert client.watchlists["42"] == []
    assert [call[0] for call in client.calls] == ["get", "remove", "get"]


def test_ambiguous_existing_get_never_recreates(tmp_path: Path) -> None:
    client = FakeClient()
    asyncio.run(map_id(tmp_path, "sample", "42"))
    with pytest.raises(AppError) as caught:
        asyncio.run(sync_screening_watchlist(screening(), result(), client, tmp_path))
    assert caught.value.code == "MCP_TOOL_ERROR"
    assert all(call[0] != "create" for call in client.calls)
    assert load_mapping(tmp_path).screenings["sample"].watchlistId == "42"


def test_only_explicitly_classified_not_found_recreates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exercise the internal branch; current Provider errors are not classified this way."""
    client = FakeClient()
    asyncio.run(map_id(tmp_path, "sample", "42"))
    from tradingview_screening.screening import watchlist_sync as module
    actual_get = module.get_managed_watchlist

    async def classified_get(client_arg: Any, identifier: str) -> Any:
        if identifier == "42":
            raise AppError("WATCHLIST_NOT_FOUND", "Confirmed missing Watchlist")
        return await actual_get(client_arg, identifier)

    monkeypatch.setattr(module, "get_managed_watchlist", classified_get)
    output = asyncio.run(sync_screening_watchlist(screening(), result(), client, tmp_path))
    assert output["status"] == "success"
    assert output["created"] is True
    assert output["watchlistId"] == "100"
    assert load_mapping(tmp_path).screenings["sample"].watchlistId == "100"


def test_add_confirmed_remove_failed_is_partial_without_rollback(tmp_path: Path) -> None:
    client = FakeClient()
    client.watchlists["42"] = ["TSE:6758"]
    client.names["42"] = "Managed"
    client.fail_action = "remove"
    asyncio.run(map_id(tmp_path, "sample", "42"))
    output = asyncio.run(sync_screening_watchlist(
        screening(), result(symbols=["TSE:7203"]), client, tmp_path,
    ))
    assert output["status"] == "partial"
    assert output["added"] == ["TSE:7203"]
    assert output["removed"] == []
    assert output["errors"][0]["code"] == "MCP_TOOL_ERROR"
    assert client.watchlists["42"] == ["TSE:6758", "TSE:7203"]
    assert [call[0] for call in client.calls].count("remove") == 1


@pytest.mark.parametrize("after_apply", [False, True])
def test_ambiguous_add_timeout_is_unconfirmed_and_never_retried(
    tmp_path: Path, after_apply: bool,
) -> None:
    client = FakeClient()
    client.watchlists["42"] = []
    client.names["42"] = "Managed"
    client.fail_action = "add"
    client.fail_after_apply = after_apply
    asyncio.run(map_id(tmp_path, "sample", "42"))
    output = asyncio.run(sync_screening_watchlist(screening(), result(), client, tmp_path))
    assert output["status"] == "failed"
    assert output["added"] == []
    assert output["errors"][0]["code"] == "WATCHLIST_WRITE_UNCONFIRMED"
    assert [call[0] for call in client.calls].count("add") == 1
    assert all(call[0] != "remove" for call in client.calls)


def test_add_success_confirmation_read_failure_is_unconfirmed(tmp_path: Path) -> None:
    client = FakeClient()
    client.watchlists["42"] = []
    client.names["42"] = "Managed"
    client.fail_get_on_call = 2
    asyncio.run(map_id(tmp_path, "sample", "42"))
    output = asyncio.run(sync_screening_watchlist(screening(), result(), client, tmp_path))
    assert output["status"] == "failed"
    assert output["added"] == []
    assert output["errors"][0]["code"] == "WATCHLIST_WRITE_UNCONFIRMED"
    assert client.watchlists["42"] == ["TSE:7203"]
    assert [call[0] for call in client.calls].count("add") == 1


def test_remove_success_confirmation_read_failure_is_unconfirmed(tmp_path: Path) -> None:
    client = FakeClient()
    client.watchlists["42"] = ["TSE:7203"]
    client.names["42"] = "Managed"
    client.fail_get_on_call = 2
    asyncio.run(map_id(tmp_path, "sample", "42"))
    output = asyncio.run(sync_screening_watchlist(
        screening(), result(symbols=[]), client, tmp_path,
    ))
    assert output["status"] == "failed"
    assert output["removed"] == []
    assert output["errors"][0]["code"] == "WATCHLIST_WRITE_UNCONFIRMED"
    assert client.watchlists["42"] == []
    assert [call[0] for call in client.calls].count("remove") == 1


def test_create_success_mapping_save_failure_reports_created_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = FakeClient()
    from tradingview_screening.screening import watchlist_sync as module

    async def fail_store(*_args: object, **_kwargs: object) -> None:
        raise AppError("WATCHLIST_MAPPING_WRITE_ERROR", "Cannot save mapping")

    monkeypatch.setattr(module, "store_managed_watchlist", fail_store)
    with pytest.raises(AppError) as caught:
        asyncio.run(sync_screening_watchlist(screening(), result(), client, tmp_path))
    assert caught.value.code == "WATCHLIST_MAPPING_WRITE_ERROR"
    assert "100" in caught.value.message
    assert [call[0] for call in client.calls] == ["create"]
    assert load_mapping(tmp_path).screenings == {}


@pytest.mark.parametrize("payload", [
    None, {}, {"watchlist": {}},
    {"watchlist": {"id": True, "name": "Managed", "symbols": []}},
    {"watchlist": {"id": 42, "name": "Managed", "symbols": [""]}},
    {"success": True, "error": "contradiction", "watchlist": {
        "id": 42, "name": "Managed", "symbols": [],
    }},
])
def test_create_get_response_schema_rejects_malformed(payload: dict | None) -> None:
    with pytest.raises(AppError) as caught:
        normalize_watchlist(response(payload))
    assert caught.value.code == "MCP_SCHEMA_MISMATCH"


def test_mutation_response_validates_id_and_ignores_content() -> None:
    normalize_watchlist_mutation(response({"watchlist_id": "42", "symbols": []}), requested_id="42")
    with pytest.raises(AppError) as caught:
        normalize_watchlist_mutation(
            response({"watchlist_id": "43", "symbols": ["TSE:7203"]}),
            requested_id="42",
        )
    assert caught.value.code == "MCP_SCHEMA_MISMATCH"


def test_provider_business_failure_is_secret_free_and_malformed_symbols_rejected() -> None:
    with pytest.raises(AppError) as business:
        normalize_watchlist(response({"success": False, "error": "secret account data"}))
    assert business.value.code == "WATCHLIST_PROVIDER_ERROR"
    assert "secret" not in business.value.message
    with pytest.raises(AppError) as malformed:
        normalize_watchlist_mutation(
            response({"watchlist_id": "42", "symbols": ["invalid symbol"]}),
            requested_id="42",
        )
    assert malformed.value.code == "MCP_SCHEMA_MISMATCH"


def test_same_watchlist_id_serializes_get_and_diff(tmp_path: Path) -> None:
    client = FakeClient()
    client.watchlists["42"] = ["TSE:7203"]
    client.names["42"] = "Managed"
    client.get_delay = 0.04

    async def exercise() -> tuple[dict, dict]:
        await map_id(tmp_path, "first", "42")
        await map_id(tmp_path, "second", "42")
        first, second = await asyncio.gather(
            sync_screening_watchlist(screening("first"), result("first"), client, tmp_path),
            sync_screening_watchlist(screening("second"), result("second"), client, tmp_path),
        )
        return first, second

    first, second = asyncio.run(exercise())
    assert first["status"] == second["status"] == "success"
    assert client.max_active_gets == 1
    assert [call[0] for call in client.calls] == ["get", "get"]


def test_different_watchlist_ids_run_concurrently(tmp_path: Path) -> None:
    client = FakeClient()
    for identifier in ("42", "43"):
        client.watchlists[identifier] = ["TSE:7203"]
        client.names[identifier] = "Managed"
    client.get_delay = 0.04

    async def exercise() -> tuple[dict, dict]:
        await map_id(tmp_path, "first", "42")
        await map_id(tmp_path, "second", "43")
        return await asyncio.gather(
            sync_screening_watchlist(screening("first"), result("first"), client, tmp_path),
            sync_screening_watchlist(screening("second"), result("second"), client, tmp_path),
        )

    first, second = asyncio.run(exercise())
    assert first["status"] == second["status"] == "success"
    assert client.max_active_gets == 2


def test_same_screening_create_race_creates_once(tmp_path: Path) -> None:
    client = FakeClient()

    async def exercise() -> tuple[dict, dict]:
        return await asyncio.gather(
            sync_screening_watchlist(screening(), result(), client, tmp_path),
            sync_screening_watchlist(screening(), result(), client, tmp_path),
        )

    first, second = asyncio.run(exercise())
    assert first["status"] == second["status"] == "success"
    assert sorted((first["created"], second["created"])) == [False, True]
    assert [call[0] for call in client.calls].count("create") == 1
    assert load_mapping(tmp_path).screenings["sample"].watchlistId == "100"


def test_different_screening_creates_merge_mapping(tmp_path: Path) -> None:
    client = FakeClient()

    async def exercise() -> tuple[dict, dict]:
        return await asyncio.gather(
            sync_screening_watchlist(screening("first"), result("first"), client, tmp_path),
            sync_screening_watchlist(screening("second"), result("second"), client, tmp_path),
        )

    first, second = asyncio.run(exercise())
    assert first["status"] == second["status"] == "success"
    assert first["watchlistId"] != second["watchlistId"]
    assert set(load_mapping(tmp_path).screenings) == {"first", "second"}


def test_sync_lock_timeout_is_explicit(tmp_path: Path) -> None:
    from tradingview_screening.screening.managed_watchlists import watchlist_lock

    async def exercise() -> None:
        async with watchlist_lock(tmp_path, "owner", "sample"):
            with pytest.raises(AppError) as caught:
                await sync_screening_watchlist(
                    screening(), result(), FakeClient(), tmp_path, lock_timeout=0.01,
                )
            assert caught.value.code == "WATCHLIST_LOCK_TIMEOUT"

    asyncio.run(exercise())


def test_real_wrappers_use_governor_and_write_nonretry(tmp_path: Path) -> None:
    class Sdk:
        def __init__(self) -> None:
            self.symbols: list[str] = []
            self.calls: list[str] = []

        async def call_tool(self, name: str, arguments: dict) -> SimpleNamespace:
            self.calls.append(name)
            if name == "mcp-watchlist-create-watchlist":
                data = {"watchlist": {"id": 42, "name": arguments["name"], "symbols": []}}
            elif name == "mcp-watchlist-get-watchlist":
                data = {"watchlist": {"id": 42, "name": "[Auto] Same Name", "symbols": self.symbols}}
            elif name == "mcp-watchlist-add-to-watchlist":
                self.symbols.extend(arguments["symbols"])
                data = {"watchlist_id": "42", "symbols": self.symbols}
            else:
                raise AssertionError(name)
            return SimpleNamespace(is_error=False, structured_content=data, content=[])

    sdk = Sdk()
    governor = RequestGovernor()
    observed: list[tuple[bool, object]] = []
    original_execute = governor.execute

    async def observed_execute(operation: Any, *, cache_key: object = None, retry: bool = True) -> Any:
        observed.append((retry, cache_key))
        return await original_execute(operation, cache_key=cache_key, retry=retry)

    governor.execute = observed_execute  # type: ignore[method-assign]
    client = TradingViewClient(governor=governor)
    client._sdk = sdk
    client._catalog = ToolCatalog(tuple(
        ToolInfo(name, None, None, {}, True, True) for name in (
            "mcp-watchlist-create-watchlist", "mcp-watchlist-get-watchlist",
            "mcp-watchlist-add-to-watchlist", "mcp-watchlist-remove-from-watchlist",
        )
    ), (), ())
    output = asyncio.run(sync_screening_watchlist(screening(), result(), client, tmp_path))
    assert output["status"] == "success"
    assert sdk.calls == [
        "mcp-watchlist-create-watchlist", "mcp-watchlist-get-watchlist",
        "mcp-watchlist-add-to-watchlist", "mcp-watchlist-get-watchlist",
    ]
    assert observed == [(False, None), (True, None), (False, None), (True, None)]
