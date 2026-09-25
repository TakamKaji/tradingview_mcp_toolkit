"""One named screening execution through the typed TradingView client."""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any

from tradingview_screening.common.errors import AppError
from tradingview_screening.integrations.tradingview.client import TradingViewClient
from tradingview_screening.integrations.tradingview.schemas import RunScreenerRequest
from tradingview_screening.integrations.tradingview.screener_normalization import normalize_screener

from .results import TOKYO
from .schema import ScreeningDefinition


def to_screener_request(screening: ScreeningDefinition) -> RunScreenerRequest:
    """Map the seven Screening fields without interpreting filter operators."""
    arguments: dict[str, Any] = {
        "market": screening.market,
        "filters": screening.model_dump(mode="json")["filters"],
        "sort_order": screening.sortOrder,
        "limit": screening.limit,
        "columns": screening.columns,
        "symbol_types": screening.symbolTypes,
    }
    if screening.sortBy is not None:
        arguments["sort_by"] = screening.sortBy
    return RunScreenerRequest.model_validate(arguments)


async def run_screening(
    screening: ScreeningDefinition, client: TradingViewClient, *, started: float | None = None,
) -> dict[str, Any]:
    request = to_screener_request(screening)
    start = started if started is not None else time.monotonic()
    response = await client.run_screener(request)
    rows = normalize_screener(response, screening.columns)
    if len(rows) > screening.limit:
        raise AppError("MCP_SCHEMA_MISMATCH", "MCP screener returned more rows than requested")
    return {
        "schemaVersion": 1,
        "status": "success",
        "operation": "screening",
        "name": screening.name,
        "executedAt": datetime.now(TOKYO).isoformat(),
        "source": "tradingview_official_mcp",
        "metadata": {
            "requestedCount": screening.limit,
            "returnedCount": len(rows),
            "partial": False,
            "durationMs": round((time.monotonic() - start) * 1000),
        },
        "results": rows,
        "errors": [],
    }
