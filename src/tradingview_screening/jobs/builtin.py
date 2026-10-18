"""Explicit builtins for the Job runner and scheduler."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any

from tradingview_screening.common.errors import AppError, ConfigError
from tradingview_screening.integrations.tradingview.client import TradingViewClient
from tradingview_screening.integrations.tradingview.schemas import (
    GetScreenerColumnsRequest,
    RunScreenerRequest,
)
from tradingview_screening.integrations.tradingview.us_sector_normalization import (
    normalize_us_sector_screener,
    require_sector_column,
)
from tradingview_screening.screening.results import TOKYO

from .schema import JobDefinition
from .us_sector import (
    build_us_sector_summary,
    require_complete_coverage,
)


async def run_us_sector_daily(client: TradingViewClient) -> dict[str, Any]:
    """Discover fields and reject incomplete coverage before publishing a summary."""
    for column in ("sector", "change"):
        response = await client.get_screener_columns(
            GetScreenerColumnsRequest(market="stock", search=column)
        )
        require_sector_column(response, column)
    response = await client.run_screener(RunScreenerRequest(
        market="america", symbol_types=["stock"], columns=["sector", "change"], limit=1000,
    ))
    retrieved_at = datetime.now(TOKYO)
    rows, total_count = normalize_us_sector_screener(response)
    require_complete_coverage(returned_count=len(rows), total_count=total_count)
    require_complete_coverage(
        returned_count=len({row["symbol"] for row in rows}),
        total_count=total_count,
    )
    return build_us_sector_summary(rows, retrieved_at=retrieved_at)


BUILTINS: dict[str, Callable[[TradingViewClient], Awaitable[dict[str, Any]]]] = {
    "us_sector_daily": run_us_sector_daily,
}


def validate_builtin_job(job: JobDefinition) -> None:
    """Validate the local contract for one builtin Job without opening a provider client."""
    if job.task.type != "builtin":
        return
    if job.task.definition not in BUILTINS:
        raise AppError("JOB_TASK_UNAVAILABLE", "Builtin Job is unavailable")
    if job.output.watchlistSync:
        raise ConfigError(
            "CONFIG_VALIDATION_ERROR",
            "Builtin Job cannot sync a Watchlist",
            "output.watchlistSync",
        )
