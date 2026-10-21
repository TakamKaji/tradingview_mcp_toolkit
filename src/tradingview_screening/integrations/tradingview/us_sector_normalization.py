"""Validate only the structured fields needed by the US sector builtin."""

from __future__ import annotations

import math
from typing import Any

from tradingview_screening.common.errors import AppError

from .schemas import ObservedReadResponse


def _structured(response: ObservedReadResponse) -> dict[str, Any]:
    content = response.structured_content
    if content is None:
        raise AppError("MCP_SCHEMA_MISMATCH", "US sector response has no structured data")
    if not content.success:
        raise AppError("PROVIDER_ERROR", "TradingView US sector request failed")
    return content.model_extra or {}


def require_sector_column(response: ObservedReadResponse, name: str) -> None:
    """Confirm the requested column is available in the stock market catalog."""
    columns = _structured(response).get("columns")
    if not isinstance(columns, list):
        raise AppError("MCP_SCHEMA_MISMATCH", "US sector column catalog is invalid")
    for column in columns:
        if not isinstance(column, dict):
            raise AppError("MCP_SCHEMA_MISMATCH", "US sector column catalog is invalid")
        if column.get("name") == name:
            markets = column.get("markets")
            if isinstance(markets, list) and "stock" in markets and all(
                isinstance(market, str) for market in markets
            ):
                return
            raise AppError("MCP_SCHEMA_MISMATCH", "US sector column is unavailable")
    raise AppError("MCP_SCHEMA_MISMATCH", "US sector column is unavailable")


def normalize_us_sector_screener(
    response: ObservedReadResponse,
) -> tuple[list[dict[str, Any]], int]:
    """Return symbol/sector/change and totalCount without parsing content text."""
    data = _structured(response).get("data")
    if not isinstance(data, dict):
        raise AppError("MCP_SCHEMA_MISMATCH", "US sector screener data is invalid")
    rows = data.get("rows")
    total_count = data.get("totalCount")
    if (
        not isinstance(rows, list)
        or type(total_count) is not int
        or total_count < 0
        or total_count < len(rows)
    ):
        raise AppError("MCP_SCHEMA_MISMATCH", "US sector screener data is invalid")
    normalized: list[dict[str, Any]] = []
    seen: dict[str, tuple[str | None, float | None]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise AppError("MCP_SCHEMA_MISMATCH", "US sector screener row is invalid")
        symbol = row.get("symbol")
        if not isinstance(symbol, str) or not symbol.strip():
            raise AppError("MCP_SCHEMA_MISMATCH", "US sector screener symbol is invalid")
        sector = row.get("sector")
        change = row.get("change")
        if sector is not None:
            if not isinstance(sector, str) or not sector.strip():
                raise AppError("MCP_SCHEMA_MISMATCH", "US sector name is invalid")
            sector = sector.strip()
        if change is not None:
            if isinstance(change, bool) or not isinstance(change, (int, float)):
                raise AppError("MCP_SCHEMA_MISMATCH", "US sector change value is invalid")
            try:
                change = float(change)
            except OverflowError as exc:
                raise AppError("MCP_SCHEMA_MISMATCH", "US sector change value is invalid") from exc
            if not math.isfinite(change):
                raise AppError("MCP_SCHEMA_MISMATCH", "US sector change value is invalid")
        pair = (sector, change)
        if symbol in seen and seen[symbol] != pair:
            raise AppError("MCP_SCHEMA_MISMATCH", "Duplicate US sector symbol has conflicting values")
        seen[symbol] = pair
        normalized.append({
            "symbol": symbol,
            "sector": sector,
            "change": change,
        })
    return normalized, total_count
