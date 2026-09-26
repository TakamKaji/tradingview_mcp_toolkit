"""Deterministic aggregation for the built-in US sector summary."""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime
from collections.abc import Iterable
from typing import Any

from tradingview_screening.common.errors import AppError

BUILTIN_NAME = "us_sector_daily"
SESSION_ASSUMPTION = (
    "Run after US regular session close; TradingView change snapshot is used as returned."
)


def _change_value(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AppError("MCP_SCHEMA_MISMATCH", "US sector change value is invalid")
    change = float(value)
    if not math.isfinite(change):
        raise AppError("MCP_SCHEMA_MISMATCH", "US sector change value is invalid")
    return change


def aggregate_us_sector_rows(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate normalized symbol/sector/change rows with one symbol equal to one vote."""
    seen: dict[str, tuple[str | None, float | None]] = {}
    excluded = 0

    for row in rows:
        if not isinstance(row, dict):
            raise AppError("MCP_SCHEMA_MISMATCH", "US sector row is invalid")

        symbol = row.get("symbol")
        if not isinstance(symbol, str) or not symbol.strip():
            raise AppError("MCP_SCHEMA_MISMATCH", "US sector symbol is invalid")

        sector_raw = row.get("sector")
        change_raw = row.get("change")
        if sector_raw is None or change_raw is None:
            normalized = (None, None)
        else:
            if not isinstance(sector_raw, str) or not sector_raw.strip():
                raise AppError("MCP_SCHEMA_MISMATCH", "US sector name is invalid")
            normalized = (sector_raw.strip(), _change_value(change_raw))

        previous = seen.get(symbol)
        if previous is not None:
            if previous != normalized:
                raise AppError(
                    "MCP_SCHEMA_MISMATCH",
                    "Duplicate US sector symbol has conflicting values",
                )
            continue
        seen[symbol] = normalized
        if normalized == (None, None):
            excluded += 1

    values: dict[str, list[float]] = defaultdict(list)
    for sector, change in seen.values():
        if sector is None or change is None:
            continue
        values[sector].append(change)

    ordered = sorted(
        (
            {
                "sector": sector,
                "meanChange": sum(changes) / len(changes),
                "sampleSize": len(changes),
            }
            for sector, changes in values.items()
        ),
        key=lambda item: (-item["meanChange"], item["sector"]),
    )

    previous_mean: float | None = None
    previous_rank = 0
    for index, item in enumerate(ordered, start=1):
        mean = item["meanChange"]
        if previous_mean is None or mean != previous_mean:
            previous_rank = index
            previous_mean = mean
        item["rank"] = previous_rank

    return {
        "validSymbolCount": sum(item["sampleSize"] for item in ordered),
        "excludedRowCount": excluded,
        "sectorCount": len(ordered),
        "results": [
            {
                "rank": item["rank"],
                "sector": item["sector"],
                "meanChange": item["meanChange"],
                "sampleSize": item["sampleSize"],
            }
            for item in ordered
        ],
    }



def require_complete_coverage(*, returned_count: int, total_count: int) -> None:
    """Reject truncated screener universes instead of presenting them as full-market results."""
    if (
        isinstance(returned_count, bool)
        or isinstance(total_count, bool)
        or not isinstance(returned_count, int)
        or not isinstance(total_count, int)
        or returned_count < 0
        or total_count < 0
        or returned_count > total_count
    ):
        raise AppError("MCP_SCHEMA_MISMATCH", "US sector screener counts are invalid")
    if returned_count < total_count:
        raise AppError(
            "US_SECTOR_COVERAGE_INCOMPLETE",
            "US sector screener result does not cover the full reported universe",
        )


def build_us_sector_summary(
    rows: Iterable[dict[str, Any]], *, retrieved_at: datetime,
) -> dict[str, Any]:
    """Build the stable public envelope from normalized US screener rows."""
    if retrieved_at.tzinfo is None or retrieved_at.utcoffset() is None:
        raise AppError("US_SECTOR_TIME_INVALID", "US sector retrieval time must be timezone-aware")
    aggregated = aggregate_us_sector_rows(rows)
    return {
        "schemaVersion": 1,
        "status": "success",
        "operation": "us_sector_summary",
        "name": BUILTIN_NAME,
        "retrievedAt": retrieved_at.isoformat(),
        "source": "tradingview_official_mcp",
        "metadata": {
            "market": "america",
            "symbolTypes": ["stock"],
            "changeMetric": "tradingview_change_snapshot_percent",
            "validSymbolCount": aggregated["validSymbolCount"],
            "excludedRowCount": aggregated["excludedRowCount"],
            "sectorCount": aggregated["sectorCount"],
            "sessionAssumption": SESSION_ASSUMPTION,
        },
        "results": aggregated["results"],
        "errors": [],
    }
