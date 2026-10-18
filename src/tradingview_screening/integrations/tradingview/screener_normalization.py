"""Normalize the observed official MCP screener response."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from tradingview_screening.common.errors import AppError

from .schemas import ObservedReadResponse


@dataclass(frozen=True)
class ScreenerSnapshot:
    rows: list[dict[str, Any]]
    total_count: int


def normalize_screener_snapshot(
    response: ObservedReadResponse, columns: list[str],
) -> ScreenerSnapshot:
    """Retain requested fields and count, rejecting ignored filters before use."""
    content = response.structured_content
    if content is None:
        raise AppError("MCP_SCHEMA_MISMATCH", "MCP screener response has no structured data")
    if not content.success:
        # Provider error details may contain request or account data; never echo them.
        code = "PROVIDER_RATE_LIMITED" if "429" in (content.error or "") else "PROVIDER_ERROR"
        raise AppError(code, "TradingView screener request failed")
    data = (content.model_extra or {}).get("data")
    if not isinstance(data, dict):
        raise AppError("MCP_SCHEMA_MISMATCH", "MCP screener response schema changed")
    if "ignored_filters" in data:
        ignored = data["ignored_filters"]
        if (
            not isinstance(ignored, list)
            or any(not isinstance(item, str) for item in ignored)
            or ignored
        ):
            raise AppError("MCP_SCHEMA_MISMATCH", "MCP screener ignored a requested filter")
    rows = data.get("rows")
    total_count = data.get("totalCount")
    if (
        not isinstance(rows, list)
        or isinstance(total_count, bool)
        or not isinstance(total_count, int)
        or total_count < 0
        or total_count < len(rows)
    ):
        raise AppError("MCP_SCHEMA_MISMATCH", "MCP screener response schema changed")
    results: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("symbol"), str) or not row["symbol"]:
            raise AppError("MCP_SCHEMA_MISMATCH", "MCP screener row schema changed")
        if any(column not in row for column in columns):
            raise AppError("MCP_SCHEMA_MISMATCH", "MCP screener row schema changed")
        normalized = {"symbol": row["symbol"]}
        normalized.update({column: row[column] for column in columns if column != "symbol"})
        results.append(normalized)
    return ScreenerSnapshot(results, total_count)


def normalize_screener(response: ObservedReadResponse, columns: list[str]) -> list[dict[str, Any]]:
    """Legacy row-only API for callers that do not consume provider counts."""
    return normalize_screener_snapshot(response, columns).rows
