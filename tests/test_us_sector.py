from __future__ import annotations

import math
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from tradingview_screening.common.errors import AppError
from tradingview_screening.jobs.us_sector import (
    aggregate_us_sector_rows,
    build_us_sector_summary,
    require_complete_coverage,
)


def row(symbol: str, sector: object = "Technology", change: object = 1.0) -> dict:
    return {"symbol": symbol, "sector": sector, "change": change}


def test_single_sector_mean_and_sample_size() -> None:
    output = aggregate_us_sector_rows([row("A", change=1.0), row("B", change=3.0)])
    assert output == {
        "validSymbolCount": 2,
        "excludedRowCount": 0,
        "sectorCount": 1,
        "results": [{"rank": 1, "sector": "Technology", "meanChange": 2.0, "sampleSize": 2}],
    }


def test_multiple_sectors_rank_descending() -> None:
    output = aggregate_us_sector_rows([
        row("A", "Energy", -1.0),
        row("B", "Technology", 2.0),
        row("C", "Financials", 0.5),
    ])
    assert [item["sector"] for item in output["results"]] == [
        "Technology", "Financials", "Energy",
    ]
    assert [item["rank"] for item in output["results"]] == [1, 2, 3]


def test_one_symbol_one_vote_not_market_cap_weighted() -> None:
    output = aggregate_us_sector_rows([
        {**row("MEGA", change=10.0), "marketCap": 10_000_000_000},
        {**row("SMALL", change=-10.0), "marketCap": 1},
    ])
    assert output["results"][0]["meanChange"] == 0.0
    assert output["results"][0]["sampleSize"] == 2


def test_ties_share_rank_and_order_by_sector_name() -> None:
    output = aggregate_us_sector_rows([
        row("A", "Technology", 1.0),
        row("B", "Energy", 1.0),
        row("C", "Utilities", 0.0),
    ])
    assert [(item["sector"], item["rank"]) for item in output["results"]] == [
        ("Energy", 1), ("Technology", 1), ("Utilities", 3),
    ]


def test_duplicate_identical_symbol_counts_once() -> None:
    output = aggregate_us_sector_rows([row("A"), row("A")])
    assert output["validSymbolCount"] == 1
    assert output["results"][0]["sampleSize"] == 1


def test_duplicate_conflicting_symbol_is_rejected() -> None:
    with pytest.raises(AppError) as caught:
        aggregate_us_sector_rows([row("A", change=1.0), row("A", change=2.0)])
    assert caught.value.code == "MCP_SCHEMA_MISMATCH"


@pytest.mark.parametrize(
    "rows",
    [
        [{"sector": "Technology", "change": 1.0}],
        [row("", change=1.0)],
        [row("A", sector=" ", change=1.0)],
        [row("A", change=True)],
        [row("A", change="1.0")],
        [row("A", change=math.inf)],
        [row("A", change=math.nan)],
    ],
)
def test_malformed_rows_are_rejected(rows: list[dict]) -> None:
    with pytest.raises(AppError) as caught:
        aggregate_us_sector_rows(rows)
    assert caught.value.code == "MCP_SCHEMA_MISMATCH"


def test_missing_sector_or_change_is_excluded() -> None:
    output = aggregate_us_sector_rows([
        row("A", sector=None, change=1.0),
        row("B", sector="Technology", change=None),
        row("C", sector="Technology", change=2.0),
    ])
    assert output["excludedRowCount"] == 2
    assert output["validSymbolCount"] == 1
    assert output["results"][0]["sampleSize"] == 1


def test_empty_valid_universe_is_stable() -> None:
    output = aggregate_us_sector_rows([])
    assert output == {
        "validSymbolCount": 0,
        "excludedRowCount": 0,
        "sectorCount": 0,
        "results": [],
    }


def test_input_order_does_not_change_output() -> None:
    rows = [
        row("A", "Technology", 2.0),
        row("B", "Energy", -1.0),
        row("C", "Technology", 0.0),
    ]
    assert aggregate_us_sector_rows(rows) == aggregate_us_sector_rows(reversed(rows))


def test_public_envelope_contains_session_contract() -> None:
    retrieved_at = datetime(2026, 9, 27, 7, 0, tzinfo=ZoneInfo("Asia/Tokyo"))
    output = build_us_sector_summary([row("A", change=1.5)], retrieved_at=retrieved_at)
    assert output["operation"] == "us_sector_summary"
    assert output["name"] == "us_sector_daily"
    assert output["retrievedAt"] == "2026-09-27T07:00:00+09:00"
    assert output["source"] == "tradingview_official_mcp"
    assert output["metadata"]["market"] == "america"
    assert output["metadata"]["symbolTypes"] == ["stock"]
    assert output["metadata"]["changeMetric"] == "tradingview_change_snapshot_percent"
    assert "regular session close" in output["metadata"]["sessionAssumption"]
    assert output["results"][0]["meanChange"] == 1.5
    assert output["errors"] == []


def test_public_envelope_requires_timezone_aware_time() -> None:
    with pytest.raises(AppError) as caught:
        build_us_sector_summary([row("A")], retrieved_at=datetime(2026, 9, 27, 7, 0))
    assert caught.value.code == "US_SECTOR_TIME_INVALID"


def test_complete_coverage_accepts_exact_count() -> None:
    require_complete_coverage(returned_count=1000, total_count=1000)


def test_incomplete_coverage_is_rejected() -> None:
    with pytest.raises(AppError) as caught:
        require_complete_coverage(returned_count=1000, total_count=5432)
    assert caught.value.code == "US_SECTOR_COVERAGE_INCOMPLETE"


@pytest.mark.parametrize(
    ("returned_count", "total_count"),
    [(True, 1), (1, True), (-1, 1), (2, 1)],
)
def test_invalid_coverage_counts_are_schema_mismatch(
    returned_count: int, total_count: int,
) -> None:
    with pytest.raises(AppError) as caught:
        require_complete_coverage(returned_count=returned_count, total_count=total_count)
    assert caught.value.code == "MCP_SCHEMA_MISMATCH"
