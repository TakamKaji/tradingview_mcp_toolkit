"""Semantic comparison of derived input-schema contracts and request models."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from tradingview_screening.integrations.tradingview.schemas import REQUEST_MODELS
from tradingview_screening.integrations.tradingview.tool_catalog import TOOL_NAME_MAP

# Independently recorded numeric and enum contract facts observed in the official
# TradingView MCP field guidance. Provider prose is deliberately not retained.
OVERLAYS: dict[tuple[str, str, str], Any] = {
    ("create_watchlist", "name", "maxLength"): 500,
    ("update_watchlist", "name", "maxLength"): 500,
    ("get_ohlcv", "count", "maximum"): 8000,
    ("get_ohlcv", "format", "enum"): ["rows", "columns"],
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


@dataclass(frozen=True)
class ContractDifference:
    """One provider/local input-contract discrepancy with an actionable location."""

    logical: str
    path: str
    kind: str
    provider: Any
    local: Any


def schema_differences(logical: str, provider_schema: dict[str, Any]) -> list[ContractDifference]:
    """Report differences without changing either contract or relaxing local constraints."""
    if logical not in REQUEST_MODELS:
        return [ContractDifference(logical, logical, "request_missing", True, False)]
    differences: list[ContractDifference] = []
    _collect_differences(
        provider_schema, REQUEST_MODELS[logical].model_json_schema(), logical, logical, differences,
    )
    return differences


def discovery_differences(provider_tools: dict[str, dict[str, Any]]) -> list[ContractDifference]:
    """Compare all discovered wire names and their input schemas against local Requests."""
    differences: list[ContractDifference] = []
    expected = set(TOOL_NAME_MAP.values())
    for wire in sorted(set(provider_tools) - expected):
        differences.append(ContractDifference("", wire, "tool_added", True, False))
    for logical, wire in TOOL_NAME_MAP.items():
        if wire not in provider_tools:
            differences.append(ContractDifference(logical, wire, "tool_missing", False, True))
        elif logical not in REQUEST_MODELS:
            differences.append(ContractDifference(logical, wire, "request_missing", True, False))
        else:
            differences.extend(schema_differences(logical, provider_tools[wire]))
    return differences


def _append(
    differences: list[ContractDifference], logical: str, path: str, kind: str,
    provider: Any, local: Any,
) -> None:
    differences.append(ContractDifference(logical, path, kind, provider, local))


def _collect_differences(
    provider: dict[str, Any], local: dict[str, Any], logical: str, path: str,
    differences: list[ContractDifference],
) -> None:
    provider_types, local_types = _types(provider), _types(local)
    if provider_types != local_types:
        kind = "nullable" if provider_types ^ local_types == {"null"} else "type"
        _append(differences, logical, path, kind, sorted(provider_types), sorted(local_types))
    if "default" in provider and (
        "default" not in local or provider["default"] != local["default"]
    ):
        # Pydantic's default=None means omitted on the wire; the Provider default
        # may intentionally differ. Surface it for review instead of rewriting it.
        _append(
            differences, logical, path, "default_review", provider["default"],
            local.get("default", "<unspecified>"),
        )
    for type_name in sorted(provider_types & local_types):
        provider_part, local_part = _branch(provider, type_name), _branch(local, type_name)
        for keyword in _CONSTRAINTS_BY_TYPE[type_name]:
            if not _constraint_matches(provider_part, local_part, logical, path.rsplit(".", 1)[-1], keyword):
                provider_value, local_value = provider_part.get(keyword), local_part.get(keyword)
                if keyword == "enum":
                    provider_value = sorted(provider_value, key=str) if provider_value is not None else None
                    local_value = sorted(local_value, key=str) if local_value is not None else None
                _append(differences, logical, f"{path}.{keyword}", "constraint", provider_value, local_value)
        if type_name == "array":
            _collect_differences(
                provider_part.get("items", {}), local_part.get("items", {}),
                logical, f"{path}[]", differences,
            )
        elif type_name == "object":
            provider_props = provider_part.get("properties", {})
            local_props = local_part.get("properties", {})
            for name in sorted(set(provider_props) - set(local_props)):
                _append(differences, logical, f"{path}.{name}", "parameter_missing", True, False)
            for name in sorted(set(local_props) - set(provider_props)):
                _append(differences, logical, f"{path}.{name}", "parameter_extra", False, True)
            provider_required = set(provider_part.get("required", []))
            local_required = set(local_part.get("required", []))
            for name in sorted(provider_required ^ local_required):
                _append(
                    differences, logical, f"{path}.{name}", "required",
                    name in provider_required, name in local_required,
                )
            for name in sorted(set(provider_props) & set(local_props)):
                _collect_differences(
                    provider_props[name], local_props[name], logical, f"{path}.{name}", differences,
                )
            _collect_extra(
                provider_part.get("additionalProperties", True),
                local_part.get("additionalProperties", True),
                logical, f"{path}.*", differences,
            )
            provider_patterns = provider_part.get("patternProperties", {})
            local_patterns = local_part.get("patternProperties", {})
            for pattern in sorted(set(provider_patterns) ^ set(local_patterns)):
                _append(
                    differences, logical, f"{path}.patternProperties[{pattern}]", "pattern",
                    pattern in provider_patterns, pattern in local_patterns,
                )
            for pattern in sorted(set(provider_patterns) & set(local_patterns)):
                _collect_extra(
                    provider_patterns[pattern], local_patterns[pattern], logical,
                    f"{path}.patternProperties[{pattern}]", differences,
                )


def _collect_extra(
    provider: Any, local: Any, logical: str, path: str,
    differences: list[ContractDifference],
) -> None:
    if isinstance(provider, dict) and isinstance(local, dict):
        _collect_differences(provider, local, logical, path, differences)
    elif not _extra_matches(provider, local, logical, path):
        _append(differences, logical, path, "additional_properties", provider, local)
