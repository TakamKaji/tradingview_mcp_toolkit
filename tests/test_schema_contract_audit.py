"""Offline drift report against the sanitized 2026-10-27 Tool Discovery."""

from __future__ import annotations

import copy
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from schema_contract import discovery_differences, schema_differences

from tradingview_screening.integrations.tradingview.schemas import REQUEST_MODELS
from tradingview_screening.integrations.tradingview.tool_catalog import TOOL_NAME_MAP

SNAPSHOT = json.loads(
    (Path(__file__).parent / "fixtures" / "tradingview_input_schemas_2026-10-27.json").read_text(
        encoding="utf-8"
    )
)


def test_latest_discovery_has_one_known_undecided_watchlist_difference() -> None:
    tools = SNAPSHOT["tools"]
    assert len(tools) == len(REQUEST_MODELS) == 35
    assert sum(len(schema.get("properties", {})) for schema in tools.values()) == 109
    assert sum(len(model.model_fields) for model in REQUEST_MODELS.values()) == 110
    assert [(item.logical, item.path, item.kind) for item in discovery_differences(tools)] == [
        ("update_watchlist", "update_watchlist.description", "parameter_extra"),
    ]


def test_discovery_audit_detects_added_missing_tools_and_missing_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tools = dict(SNAPSHOT["tools"])
    removed = TOOL_NAME_MAP["get_ohlcv"]
    del tools[removed]
    tools["mcp-tv-new-read"] = {"type": "object", "properties": {}}
    findings = discovery_differences(tools)
    assert {(item.path, item.kind) for item in findings} >= {
        (removed, "tool_missing"), ("mcp-tv-new-read", "tool_added"),
    }

    monkeypatch.delitem(REQUEST_MODELS, "get_ohlcv")
    findings = discovery_differences(SNAPSHOT["tools"])
    assert ("get_ohlcv", "request_missing") in {
        (item.logical, item.kind) for item in findings
    }


@pytest.mark.parametrize("logical,mutation,expected", [
    (
        "get_ohlcv",
        lambda x: x["properties"].update({"future_field": {"type": "string"}}),
        ("get_ohlcv.future_field", "parameter_missing"),
    ),
    (
        "get_ohlcv",
        lambda x: x["properties"].pop("date_from"),
        ("get_ohlcv.date_from", "parameter_extra"),
    ),
    (
        "get_ohlcv",
        lambda x: x["required"].append("date_from"),
        ("get_ohlcv.date_from", "required"),
    ),
    (
        "get_ohlcv",
        lambda x: x["properties"]["date_from"].update({"type": "integer"}),
        ("get_ohlcv.date_from", "type"),
    ),
    (
        "get_ohlcv",
        lambda x: x["properties"]["date_from"].update({"type": ["string", "null"]}),
        ("get_ohlcv.date_from", "nullable"),
    ),
    (
        "get_ohlcv",
        lambda x: x["properties"]["format"].update({"enum": ["rows"]}),
        ("get_ohlcv.format.enum", "constraint"),
    ),
    (
        "get_ohlcv",
        lambda x: x["properties"]["count"].update({"maximum": 7999}),
        ("get_ohlcv.count.maximum", "constraint"),
    ),
    (
        "get_ohlcv",
        lambda x: x["properties"]["date_to"].update({"default": "2026-01-01"}),
        ("get_ohlcv.date_to", "default_review"),
    ),
    (
        "create_watchlist",
        lambda x: x["properties"]["name"].update({"maxLength": 501}),
        ("create_watchlist.name.maxLength", "constraint"),
    ),
])
def test_audit_reports_relevant_schema_changes(
    logical: str, mutation: Callable[[dict[str, Any]], None], expected: tuple[str, str],
) -> None:
    schema = copy.deepcopy(SNAPSHOT["tools"][TOOL_NAME_MAP[logical]])
    mutation(schema)
    findings = schema_differences(logical, schema)
    assert expected in {(item.path, item.kind) for item in findings}


def test_provider_default_missing_is_unknown_not_assumed_to_match() -> None:
    schema = SNAPSHOT["tools"][TOOL_NAME_MAP["get_ohlcv"]]
    assert "default" not in schema["properties"]["count"]
    assert all(item.kind != "default_review" for item in schema_differences("get_ohlcv", schema))
