"""One named screening execution through the typed TradingView client."""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any

from tradingview_screening.common.errors import AppError
from tradingview_screening.integrations.tradingview.client import TradingViewClient
from tradingview_screening.integrations.tradingview.schemas import RunScreenerRequest
from tradingview_screening.integrations.tradingview.screener_normalization import (
    normalize_screener_snapshot,
)

from .results import TOKYO
from .schema import ScreeningDefinition


def to_screener_request(screening: ScreeningDefinition) -> RunScreenerRequest:
    """Map Screening selectors without interpreting Provider filter operators."""
    arguments: dict[str, Any] = {
        "market": screening.market,
        "sort_order": screening.sortOrder,
        "limit": screening.limit,
        "columns": screening.columns,
        "symbol_types": screening.symbolTypes,
    }
    if screening.filters:
        arguments["filters"] = screening.model_dump(mode="json")["filters"]
    if screening.filterPreset is not None:
        arguments["filter_preset"] = screening.filterPreset
    if screening.symbolset is not None:
        arguments["symbolset"] = screening.symbolset
    if screening.sortBy is not None:
        arguments["sort_by"] = screening.sortBy
    return RunScreenerRequest.model_validate(arguments)


async def run_screening(
    screening: ScreeningDefinition, client: TradingViewClient, *, started: float | None = None,
) -> dict[str, Any]:
    request = to_screener_request(screening)
    start = started if started is not None else time.monotonic()
    response = await client.run_screener(request)
    snapshot = normalize_screener_snapshot(response, screening.columns)
    rows = snapshot.rows
    if len(rows) > screening.limit:
        raise AppError("MCP_SCHEMA_MISMATCH", "MCP screener returned more rows than requested")
    returned_count = len(rows)
    return {
        "schemaVersion": 1,
        "status": "success",
        "operation": "screening",
        "name": screening.name,
        "executedAt": datetime.now(TOKYO).isoformat(),
        "source": "tradingview_official_mcp",
        "metadata": {
            "requestedCount": screening.limit,
            "requestedLimit": screening.limit,
            "totalCount": snapshot.total_count,
            "returnedCount": returned_count,
            "limitReached": returned_count >= screening.limit,
            "completeCoverage": (
                returned_count == snapshot.total_count
                and len({row["symbol"] for row in rows}) == snapshot.total_count
            ),
            "partial": False,
            "durationMs": round((time.monotonic() - start) * 1000),
        },
        "results": rows,
        "errors": [],
    }
