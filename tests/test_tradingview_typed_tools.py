from __future__ import annotations

import asyncio
import copy
import inspect
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, get_type_hints

import pytest
from pydantic import ValidationError
from schema_contract import OVERLAYS, schema_is_compatible

from tradingview_screening.common.errors import AppError
from tradingview_screening.integrations.tradingview.client import (
    NON_RETRY_TOOL_NAMES,
    WRITE_TOOL_NAMES,
    ToolCallData,
    TradingViewClient,
)
from tradingview_screening.integrations.tradingview.schemas import (
    REQUEST_MODELS,
    AddToWatchlistRequest,
    ContentBlock,
    CreateAlertRequest,
    GetEconomicCalendarRequest,
    GetOhlcvRequest,
    GetSymbolDataBatchRequest,
    ObservedReadData,
    ObservedReadResponse,
    RunScreenerRequest,
    TypedToolResponse,
    UpdateAlertRequest,
)
from tradingview_screening.integrations.tradingview.tool_catalog import (
    EXPECTED_TOOLS,
    TOOL_NAME_MAP,
)

SNAPSHOT = json.loads(
    (Path(__file__).parent / "fixtures" / "tradingview_input_schemas_2026-09-25.json").read_text(encoding="utf-8")
)
LATEST_SNAPSHOT = json.loads(
    (Path(__file__).parent / "fixtures" / "tradingview_input_schemas_2026-10-18.json").read_text(
        encoding="utf-8"
    )
)
LOGICAL_NAMES = tuple(TOOL_NAME_MAP)
OBSERVED_READ_NAMES = frozenset({
    "search_symbols", "get_ohlcv", "get_symbol_data", "get_symbol_data_batch",
    "get_screener_columns", "run_screener", "get_technicals_rating", "get_economic_symbols",
})


def _sample(schema: dict[str, Any]) -> Any:
    if "anyOf" in schema:
        schema = next(part for part in schema["anyOf"] if part.get("type") != "null")
    if "enum" in schema:
        return schema["enum"][0]
    kind = schema.get("type")
    if isinstance(kind, list):
        kind = next(value for value in kind if value != "null")
    return {
        "string": "sample", "number": 1.0, "integer": 1, "boolean": True,
        "array": [], "object": {},
    }[kind]


def _minimal(logical: str) -> dict[str, Any]:
    schema = SNAPSHOT["tools"][TOOL_NAME_MAP[logical]]
    return {name: None if "null" in prop.get("type", []) else _sample(prop)
            for name in schema.get("required", [])
            if (prop := schema["properties"][name])}


def test_complete_logical_wire_request_wrapper_and_policy_sets() -> None:
    assert len(TOOL_NAME_MAP) == len(set(TOOL_NAME_MAP)) == 35
    assert len(set(TOOL_NAME_MAP.values())) == len(EXPECTED_TOOLS) == 35
    assert set(REQUEST_MODELS) == set(TOOL_NAME_MAP)
    assert len(set(REQUEST_MODELS.values())) == 35
    assert set(SNAPSHOT["tools"]) == set(EXPECTED_TOOLS)
    assert SNAPSHOT["retrievedAt"] == "2026-09-25"
    assert SNAPSHOT["protocolVersion"] == "2025-11-25"
    assert SNAPSHOT["serverVersion"] == "1.30.0"
    assert LATEST_SNAPSHOT["retrievedAt"] == "2026-10-18"
    assert LATEST_SNAPSHOT["protocolVersion"] == "2025-11-25"
    assert LATEST_SNAPSHOT["serverVersion"] == "1.30.0"
    assert set(LATEST_SNAPSHOT["tools"]) == set(EXPECTED_TOOLS)
    assert len(WRITE_TOOL_NAMES) == 10
    assert len(set(TOOL_NAME_MAP) - WRITE_TOOL_NAMES) == 25
    assert NON_RETRY_TOOL_NAMES == WRITE_TOOL_NAMES | {"get_active_watchlist"}
    for logical in TOOL_NAME_MAP:
        assert inspect.iscoroutinefunction(getattr(TradingViewClient, logical))
        hints = get_type_hints(getattr(TradingViewClient, logical))
        assert hints["request"] is REQUEST_MODELS[logical]
        assert hints["return"] is (ObservedReadResponse if logical in OBSERVED_READ_NAMES else TypedToolResponse)


def _without_descriptions(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _without_descriptions(item) for key, item in value.items()
                if key != "description"}
    if isinstance(value, list):
        return [_without_descriptions(item) for item in value]
    return value


@pytest.mark.parametrize("logical", LOGICAL_NAMES)
def test_october_input_schema_preserves_existing_tool_contract(logical: str) -> None:
    wire = TOOL_NAME_MAP[logical]
    old = SNAPSHOT["tools"][wire]
    current = copy.deepcopy(LATEST_SNAPSHOT["tools"][wire])
    added = set(current.get("properties", {})) - set(old.get("properties", {}))
    if logical == "get_ohlcv":
        assert added == {"date_from", "date_to", "format"}
        for name in added:
            assert name not in current.get("required", [])
            del current["properties"][name]
    else:
        assert not added
        assert schema_is_compatible(logical, current)
    assert _without_descriptions(current) == _without_descriptions(old)
    if logical in {"run_screener", "get_screener_columns"}:
        assert current == old


@pytest.mark.parametrize("logical", LOGICAL_NAMES)
def test_request_minimal_required_extra_optional_nullable_and_snapshot(logical: str) -> None:
    request_type = REQUEST_MODELS[logical]
    provider = SNAPSHOT["tools"][TOOL_NAME_MAP[logical]]
    minimal = _minimal(logical)
    assert schema_is_compatible(logical, provider)
    request = request_type.model_validate(minimal)
    assert request.model_dump(mode="json", exclude_unset=True) == minimal

    for required in provider.get("required", []):
        missing = dict(minimal)
        del missing[required]
        with pytest.raises(ValidationError):
            request_type.model_validate(missing)

    with pytest.raises(ValidationError):
        request_type.model_validate({**minimal, "unexpected_field": 1})

    for name, prop in provider.get("properties", {}).items():
        if name in provider.get("required", []):
            continue
        sample = _sample(request_type.model_json_schema()["properties"][name])
        populated = request_type.model_validate({**minimal, name: sample})
        assert populated.model_dump(mode="json", exclude_unset=True)[name] == sample
        if "null" in prop.get("type", []):
            explicit_null = request_type.model_validate({**minimal, name: None})
            assert name in explicit_null.model_dump(mode="json", exclude_unset=True)
        else:
            with pytest.raises(ValidationError):
                request_type.model_validate({**minimal, name: None})


@pytest.mark.parametrize("logical", LOGICAL_NAMES)
def test_all_wrappers_map_to_wire_and_correct_retry_policy(logical: str, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, dict[str, Any], bool, object]] = []
    client = TradingViewClient()

    async def fake_call(name: str, args: dict[str, Any], *, retry: bool, cache_key: object) -> ToolCallData:
        calls.append((name, args, retry, cache_key))
        return ToolCallData(structured_content={"success": True, "value": 1},
                            content=[{"type": "text", "text": "provider text"}])

    monkeypatch.setattr(client, "_call_tool", fake_call)

    async def scenario() -> None:
        request = REQUEST_MODELS[logical].model_validate(_minimal(logical))
        result = await getattr(client, logical)(request)
        assert isinstance(result, TypedToolResponse)
        assert isinstance(result, ObservedReadResponse) == (logical in OBSERVED_READ_NAMES)
        assert not isinstance(result, ToolCallData)
        if logical in OBSERVED_READ_NAMES:
            assert isinstance(result.structured_content, ObservedReadData)
            assert result.structured_content.success is True
            assert result.structured_content.model_extra == {"value": 1}
        else:
            assert result.structured_content == {"success": True, "value": 1}
        assert result.content[0].text == "provider text"
        assert calls == [(TOOL_NAME_MAP[logical], request.model_dump(mode="json", exclude_unset=True),
                          logical not in NON_RETRY_TOOL_NAMES, None)]

    asyncio.run(scenario())


def test_documented_boundaries_and_strict_types() -> None:
    assert GetOhlcvRequest(symbol="TSE:7203", count=5000).count == 5000
    with pytest.raises(ValidationError):
        GetOhlcvRequest(symbol="TSE:7203", count=5001)
    with pytest.raises(ValidationError):
        GetOhlcvRequest(symbol="TSE:7203", count=True)
    assert len(GetSymbolDataBatchRequest(symbols=["TSE:7203"] * 50).symbols) == 50
    with pytest.raises(ValidationError):
        GetSymbolDataBatchRequest(symbols=["TSE:7203"] * 51)
    assert GetEconomicCalendarRequest(min_importance=-1).min_importance == -1
    with pytest.raises(ValidationError):
        GetEconomicCalendarRequest(min_importance=True)
    with pytest.raises(ValidationError):
        GetEconomicCalendarRequest(min_importance=2)
    with pytest.raises(ValidationError):
        AddToWatchlistRequest(watchlist_id="x", symbols=[1])


@pytest.mark.parametrize(("logical", "field", "keyword"), tuple(OVERLAYS))
def test_every_description_overlay_boundary(logical: str, field: str, keyword: str) -> None:
    request_type = REQUEST_MODELS[logical]
    baseline = _minimal(logical)
    bound, _source = OVERLAYS[(logical, field, keyword)]
    if keyword == "enum":
        for value in bound:
            assert getattr(request_type.model_validate({**baseline, field: value}), field) == value
        invalid: Any = "invalid-enum-value"
    elif keyword == "maxLength":
        assert len(getattr(request_type.model_validate({**baseline, field: "x" * bound}), field)) == bound
        invalid = "x" * (bound + 1)
    elif keyword == "maxItems":
        item = _sample(SNAPSHOT["tools"][TOOL_NAME_MAP[logical]]["properties"][field]["items"])
        assert len(getattr(request_type.model_validate({**baseline, field: [item] * bound}), field)) == bound
        invalid = [item] * (bound + 1)
    elif keyword == "maximum":
        assert getattr(request_type.model_validate({**baseline, field: bound}), field) == bound
        invalid = bound + 1
    else:
        assert keyword == "minimum"
        assert getattr(request_type.model_validate({**baseline, field: bound}), field) == bound
        invalid = bound - 1
    with pytest.raises(ValidationError):
        request_type.model_validate({**baseline, field: invalid})


def test_open_filters_pattern_properties_and_json_safety() -> None:
    filters = {"pe": [None, 15], "index": "S&P 500", "future_beta_field": {"nested": [1, True]}}
    request = RunScreenerRequest(filters=filters)
    assert request.model_dump(mode="json", exclude_unset=True)["filters"] == filters
    assert CreateAlertRequest(symbol="TSE:7203", webhook={"url": "https://example.test"}).model_extra is not None
    assert CreateAlertRequest(symbol="TSE:7203", monitor=False).model_extra is not None
    assert UpdateAlertRequest(alert_id=1, webhook=None).model_extra == {"webhook": None}
    with pytest.raises(ValidationError):
        CreateAlertRequest(symbol="TSE:7203", unexpected=1)
    with pytest.raises(ValidationError):
        UpdateAlertRequest(alert_id=1, monitor=True)
    with pytest.raises(ValidationError):
        RunScreenerRequest(filters={"x": float("nan")})


def test_response_envelope_extra_blocks_and_schema_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    response = TypedToolResponse.model_validate({
        "structured_content": {"rows": [{"new_beta_field": 3}]},
        "content": [{"type": "text", "text": "analysis"}, {"type": "future", "futureField": [1]}],
        "provider_added": True,
    })
    assert response.structured_content["rows"][0]["new_beta_field"] == 3
    assert isinstance(response.content[0], ContentBlock)
    assert response.content[1].model_extra == {"futureField": [1]}
    assert response.model_extra == {"provider_added": True}
    assert TypedToolResponse.model_validate(response.model_dump(mode="python")) == response
    text_only = ObservedReadResponse.model_validate({
        "structured_content": None,
        "content": [{"type": "text", "text": '{"success": true, "count": 2}'}],
    })
    assert text_only.structured_content is None
    assert text_only.content[0].text == '{"success": true, "count": 2}'
    assert ObservedReadResponse.model_validate(text_only.model_dump(mode="python")) == text_only
    for bad in (
        {"structured_content": {}, "content": [{"type": "text", "text": 2}]},
        {"structured_content": {}, "content": [{"type": "text"}]},
        {"structured_content": {}, "content": "not-a-list"},
        {"structured_content": {}, "content": [{"type": "future", "bad": float("inf")}]},
        {"structured_content": {}},
    ):
        with pytest.raises(ValidationError):
            TypedToolResponse.model_validate(bad)

    client = TradingViewClient()

    async def bad_call(*_args: object, **_kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(structured_content={"success": True}, content=[{"type": "text", "text": 2}])

    monkeypatch.setattr(client, "_call_tool", bad_call)

    async def scenario() -> None:
        with pytest.raises(AppError) as caught:
            await client.get_ohlcv(GetOhlcvRequest(symbol="TSE:7203"))
        assert caught.value.code == "MCP_SCHEMA_MISMATCH"

    asyncio.run(scenario())


def test_observed_read_optional_nulls_and_roundtrip() -> None:
    response = ObservedReadResponse.model_validate({
        "structured_content": {"success": True, "error": None, "count": None, "missing_count": None,
                               "future_field": ["ok"]},
        "content": [{"type": "future", "payload": {"beta": 1}}],
    })
    assert response.structured_content is not None
    assert response.structured_content.error is None
    assert ObservedReadResponse.model_validate(response.model_dump(mode="python")) == response


@pytest.mark.parametrize("logical", sorted(OBSERVED_READ_NAMES))
def test_observed_read_response_fields_and_provider_business_failure(
    logical: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = TradingViewClient()

    async def fake_call(*_args: object, **_kwargs: object) -> ToolCallData:
        return ToolCallData(
            structured_content={"success": False, "error": "provider rejected request", "count": 0,
                                "missing_count": 1, "future_data": {"new": [1, True]}},
            content=[{"type": "text", "text": "provider text"}],
        )

    monkeypatch.setattr(client, "_call_tool", fake_call)

    async def scenario() -> None:
        response = await getattr(client, logical)(REQUEST_MODELS[logical].model_validate(_minimal(logical)))
        assert isinstance(response, ObservedReadResponse)
        assert response.structured_content is not None
        assert response.structured_content.success is False
        assert response.structured_content.error == "provider rejected request"
        assert response.structured_content.count == 0
        assert response.structured_content.missing_count == 1
        assert response.structured_content.model_extra == {"future_data": {"new": [1, True]}}

    asyncio.run(scenario())


@pytest.mark.parametrize("payload", [
    {}, {"success": 1}, {"success": "true"},
    {"success": True, "error": 7}, {"success": True, "count": True},
    {"success": True, "missing_count": "1"}, {"success": True, "future": float("nan")},
])
def test_observed_read_response_rejects_malformed_stable_fields(
    payload: dict[str, Any], monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = TradingViewClient()

    async def fake_call(*_args: object, **_kwargs: object) -> ToolCallData:
        return ToolCallData(structured_content=payload, content=[])

    monkeypatch.setattr(client, "_call_tool", fake_call)

    async def scenario() -> None:
        with pytest.raises(AppError) as caught:
            await client.search_symbols(REQUEST_MODELS["search_symbols"].model_validate(_minimal("search_symbols")))
        assert caught.value.code == "MCP_SCHEMA_MISMATCH"

    asyncio.run(scenario())


def test_mutated_or_constructed_request_is_revalidated_before_send(monkeypatch: pytest.MonkeyPatch) -> None:
    client = TradingViewClient()

    async def fail_call(*_args: object, **_kwargs: object) -> ToolCallData:
        pytest.fail("invalid request reached MCP")

    monkeypatch.setattr(client, "_call_tool", fail_call)

    async def scenario() -> None:
        request = GetSymbolDataBatchRequest(symbols=["TSE:7203"])
        request.symbols.append(7)
        with pytest.raises(AppError) as caught:
            await client.get_symbol_data_batch(request)
        assert caught.value.code == "MCP_ARGUMENT_ERROR"
        constructed = GetOhlcvRequest.model_construct(count=True)
        with pytest.raises(AppError) as caught:
            await client.get_ohlcv(constructed)
        assert caught.value.code == "MCP_ARGUMENT_ERROR"

    asyncio.run(scenario())


def test_semantic_drift_catches_relevant_changes_without_json_exact_match() -> None:
    baseline = SNAPSHOT["tools"][TOOL_NAME_MAP["get_symbol_data_batch"]]
    assert schema_is_compatible("get_symbol_data_batch", baseline)
    variants = []
    for mutate in (
        lambda x: x["properties"].update({"new_field": {"type": "string"}}),
        lambda x: x["required"].remove("symbols"),
        lambda x: x["properties"]["symbols"].update({"type": "array"}),
        lambda x: x["properties"]["symbols"]["items"].update({"type": "integer"}),
        lambda x: x.update({"additionalProperties": True}),
        lambda x: x["properties"]["symbols"].update({"maxItems": 51}),
        lambda x: x["properties"]["symbols"].update({"uniqueItems": True}),
    ):
        changed = copy.deepcopy(baseline)
        mutate(changed)
        variants.append(changed)
    assert all(not schema_is_compatible("get_symbol_data_batch", changed) for changed in variants)

    nested = copy.deepcopy(SNAPSHOT["tools"][TOOL_NAME_MAP["create_alert"]])
    nested["properties"]["conditions"]["items"]["properties"] = {"new": {"type": "string"}}
    assert not schema_is_compatible("create_alert", nested)

    required = copy.deepcopy(baseline)
    required["required"].append("columns")
    assert not schema_is_compatible("get_symbol_data_batch", required)
    typed_extra = copy.deepcopy(SNAPSHOT["tools"][TOOL_NAME_MAP["run_screener"]])
    typed_extra["properties"]["filters"]["additionalProperties"] = {"type": "string"}
    assert not schema_is_compatible("run_screener", typed_extra)
    nested = copy.deepcopy(SNAPSHOT["tools"][TOOL_NAME_MAP["create_alert"]])
    nested["properties"]["conditions"]["items"]["required"] = ["new"]
    assert not schema_is_compatible("create_alert", nested)
    nested = copy.deepcopy(SNAPSHOT["tools"][TOOL_NAME_MAP["create_alert"]])
    nested["patternProperties"] = {"^(webhook)$": True}
    assert not schema_is_compatible("create_alert", nested)

    documented = copy.deepcopy(SNAPSHOT["tools"][TOOL_NAME_MAP["get_ohlcv"]])
    documented["properties"]["count"]["description"] = "count is unrestricted"
    assert not schema_is_compatible("get_ohlcv", documented)
    assert len(OVERLAYS) >= 20


def test_enum_order_is_semantically_ignored() -> None:
    schema = copy.deepcopy(SNAPSHOT["tools"][TOOL_NAME_MAP["get_technicals_rating"]])
    schema["properties"]["interval"]["enum"] = ["1W", "1M", "1D", "4h", "2h", "1h", "30m", "15m", "5m", "1m"]
    assert schema_is_compatible("get_technicals_rating", schema)
