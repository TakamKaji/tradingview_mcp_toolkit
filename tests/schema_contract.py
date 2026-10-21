"""Semantic comparison of derived input-schema contracts and request models."""

from __future__ import annotations

import json
from typing import Any

from tradingview_screening.integrations.tradingview.schemas import REQUEST_MODELS

# Independently recorded numeric and enum contract facts observed in the official
# TradingView MCP field guidance. Provider prose is deliberately not retained.
OVERLAYS: dict[tuple[str, str, str], Any] = {
    ("create_watchlist", "name", "maxLength"): 500,
    ("update_watchlist", "name", "maxLength"): 500,
    ("get_ohlcv", "count", "maximum"): 5000,
    ("get_ohlcv", "interval", "enum"): [
        "1m",
        "5m",
        "15m",
        "30m",
        "1h",
        "4h",
        "1D",
        "1W",
        "M",
        "1mo",
        "month",
    ],
    ("get_economic_symbols", "category", "enum"): [
        "gdp",
        "lbr",
        "prce",
        "hlth",
        "mny",
        "trd",
        "gov",
        "bsnss",
        "cnsm",
        "hse",
        "txs",
        "enrg",
        "clmt",
    ],
    ("search_symbols", "type_filter", "enum"): [
        "stock",
        "etf",
        "bond",
        "forex",
        "index",
        "futures",
        "crypto",
        "all",
    ],
    ("run_screener", "sort_order", "enum"): ["asc", "desc"],
    ("run_screener", "limit", "maximum"): 1000,
    ("run_screener", "filter_preset", "enum"): [
        "pullback_with_reversal",
        "breakout_with_volume",
        "oversold_healthy",
        "earnings_runup",
        "relative_strength",
        "new_highs",
    ],
    ("get_symbol_data_batch", "symbols", "maxItems"): 50,
    ("get_screener_columns", "market", "enum"): ["stock", "etf", "crypto", "bond", "all"],
    ("get_technicals_rating", "interval", "enum"): [
        "1m",
        "5m",
        "15m",
        "30m",
        "1h",
        "2h",
        "4h",
        "1D",
        "1W",
        "1M",
    ],
    ("get_news", "lang", "enum"): [
        "en",
        "ru",
        "de",
        "fr",
        "es",
        "pt",
        "it",
        "pl",
        "tr",
        "ar",
        "he",
        "ko",
        "ja",
        "vi",
        "th",
        "ms",
        "id",
        "zh-Hans",
        "zh-Hant",
        "ro",
        "en_IN",
    ],
    ("get_news", "limit", "maximum"): 200,
    ("get_news_story", "user_prostatus", "enum"): ["pro", "non_pro"],
    ("get_financials", "period", "enum"): ["fy", "fq", "ttm", "fh", "current"],
    ("get_financial_history", "period", "enum"): ["fq", "fy"],
    ("get_documents", "category", "enum"): [
        "all",
        "annual_reports",
        "quarterly_reports",
        "interim_reports",
        "company_events",
        "insider_transactions",
        "transcripts",
        "presentations",
        "press_releases",
        "other",
        "10-K",
        "10-Q",
        "8-K",
    ],
    ("get_documents", "event", "enum"): ["earning", "corporate_event"],
    ("get_economic_calendar", "category", "enum"): [
        "gdp",
        "bonds",
        "business",
        "consumer",
        "goverment",
        "health",
        "housing",
        "labor",
        "money",
        "prices",
        "trade",
        "taxes",
        "all",
    ],
    ("get_economic_calendar", "min_importance", "minimum"): -1,
    ("get_economic_calendar", "min_importance", "maximum"): 1,
    ("get_dividends_calendar", "limit", "maximum"): 200,
    ("create_alert", "condition", "enum"): ["cross", "cross_up", "cross_down", "greater", "less"],
    ("create_alert", "message", "maxLength"): 4000,
    ("create_alert", "name", "maxLength"): 300,
    ("get_alerts_log", "limit", "maximum"): 2000,
}

_CONSTRAINTS_BY_TYPE = {
    "string": ("enum", "const", "minLength", "maxLength", "pattern", "format"),
    "integer": ("enum", "const", "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "multipleOf"),
    "number": ("enum", "const", "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "multipleOf"),
    "boolean": ("enum", "const"),
    "null": ("enum", "const"),
    "array": ("minItems", "maxItems", "uniqueItems"),
    "object": ("minProperties", "maxProperties", "propertyNames"),
}


def _types(schema: dict[str, Any]) -> set[str]:
    if "anyOf" in schema:
        return set().union(*(_types(branch) for branch in schema["anyOf"]))
    if "oneOf" in schema:
        return set().union(*(_types(branch) for branch in schema["oneOf"]))
    value = schema.get("type")
    return set(value) if isinstance(value, list) else {value} if isinstance(value, str) else set()


def _branch(schema: dict[str, Any], type_name: str) -> dict[str, Any]:
    return next((part for part in schema.get("anyOf", schema.get("oneOf", [schema]))
                 if type_name in _types(part)), {})


def _enum_set(values: list[Any]) -> set[str]:
    return {json.dumps(value, sort_keys=True) for value in values}


def _constraint_matches(
    source: dict[str, Any], target: dict[str, Any], logical: str, path: str, keyword: str,
) -> bool:
    source_value = source.get(keyword)
    target_value = target.get(keyword)
    if keyword == "enum":
        if source_value is not None:
            return target_value is not None and _enum_set(source_value) == _enum_set(target_value)
        if target_value is not None:
            overlay = OVERLAYS.get((logical, path, keyword))
            return overlay is not None and _enum_set(overlay) == _enum_set(target_value)
        return True
    if source_value is not None:
        return source_value == target_value
    if target_value is not None:
        overlay = OVERLAYS.get((logical, path, keyword))
        return overlay is not None and overlay == target_value
    return True


def _extra_matches(source: Any, target: Any, logical: str, path: str) -> bool:
    if isinstance(source, bool):
        if source is False:
            return target is False
        return target is True or isinstance(target, dict) and target.get("$ref") == "#/$defs/JsonValue"
    return isinstance(source, dict) and isinstance(target, dict) and _node_matches(source, target, logical, path)


def _node_matches(source: dict[str, Any], target: dict[str, Any], logical: str, path: str) -> bool:
    if _types(source) != _types(target):
        return False
    for kind in _types(source):
        source_part, target_part = _branch(source, kind), _branch(target, kind)
        if any(not _constraint_matches(source_part, target_part, logical, path, key)
               for key in _CONSTRAINTS_BY_TYPE[kind]):
            return False
        if kind == "array" and not _node_matches(
            source_part.get("items", {}), target_part.get("items", {}), logical, path,
        ):
            return False
        if kind == "object":
            source_props = source_part.get("properties", {})
            target_props = target_part.get("properties", {})
            if set(source_props) != set(target_props):
                return False
            if set(source_part.get("required", [])) != set(target_part.get("required", [])):
                return False
            if not _extra_matches(
                source_part.get("additionalProperties", True),
                target_part.get("additionalProperties", True), logical, path,
            ):
                return False
            source_patterns = source_part.get("patternProperties", {})
            target_patterns = target_part.get("patternProperties", {})
            if set(source_patterns) != set(target_patterns):
                return False
            if any(not _extra_matches(source_patterns[key], target_patterns[key], logical, path)
                   for key in source_patterns):
                return False
            if any(not _node_matches(source_props[key], target_props[key], logical, key)
                   for key in source_props):
                return False
    return True


def schema_is_compatible(logical: str, live_schema: dict[str, Any]) -> bool:
    """Compare shapes recursively while ignoring Pydantic titles/defaults and enum order."""
    return _node_matches(live_schema, REQUEST_MODELS[logical].model_json_schema(), logical, "")
