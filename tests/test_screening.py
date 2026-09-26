from __future__ import annotations

import json
from pathlib import Path

import pytest

from tradingview_screening.common.errors import ConfigError
from tradingview_screening.screening.validators import load_screening, validate_screening


def minimal_screening() -> dict:
    return {
        "schemaVersion": 1,
        "name": "test_screen",
        "market": "japan",
        "symbolTypes": ["stock"],
        "columns": ["close"],
        "limit": 1,
    }


def test_minimal_screening() -> None:
    screen = validate_screening(minimal_screening())
    assert screen.name == "test_screen"
    assert screen.filters == {}


def test_sample_screening() -> None:
    path = Path(__file__).resolve().parents[1] / "screenings" / "sample_standard_screen.json"
    screen = load_screening(path)
    assert screen.name == "sample_standard_screen"
    assert screen.filters["price_earnings_ttm"] == (None, 15)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schemaVersion", 2),
        ("schemaVersion", True),
        ("schemaVersion", 1.0),
        ("name", "  "),
        ("market", ""),
        ("symbolTypes", []),
        ("symbolTypes", ["  "]),
        ("columns", []),
        ("columns", ["  "]),
        ("limit", 0),
        ("limit", 1001),
        ("limit", True),
        ("sortOrder", "up"),
        ("sortBy", "  "),
    ],
)
def test_invalid_screening_field(field: str, value: object) -> None:
    data = minimal_screening()
    data[field] = value
    with pytest.raises(ConfigError) as caught:
        validate_screening(data)
    assert caught.value.code == "CONFIG_VALIDATION_ERROR"


@pytest.mark.parametrize("location", ["root", "watchlist"])
def test_unknown_screening_key(location: str) -> None:
    data = minimal_screening()
    if location == "root":
        data["other"] = 1
    else:
        data["watchlist"] = {"enabled": False, "other": 1}
    with pytest.raises(ConfigError, match="Invalid screening definition"):
        validate_screening(data)


def test_valid_filters() -> None:
    data = minimal_screening()
    data["filters"] = {"close": [100, 5000], "market_cap_basic": [1000000000, None]}
    screen = validate_screening(data)
    assert screen.filters["close"] == (100, 5000)
    assert screen.model_dump(mode="json")["filters"]["close"] == [100, 5000]


def test_special_filters_are_preserved() -> None:
    data = minimal_screening()
    data["filters"] = {
        "index": "Nikkei 225",
        "sector": "Technology",
        "industry": "Semiconductors",
        "analyst_rating": "Buy",
    }
    screen = validate_screening(data)
    assert screen.model_dump(mode="json")["filters"] == data["filters"]


@pytest.mark.parametrize("filters", [
    {"close": "Technology"},
    {"sector": [1, 5]},
    {"industry": "   "},
])
def test_filter_value_shape_matches_normal_and_special_contract(filters: object) -> None:
    data = minimal_screening()
    data["filters"] = filters
    with pytest.raises(ConfigError) as caught:
        validate_screening(data)
    assert caught.value.code == "CONFIG_VALIDATION_ERROR"


def test_limit_upper_bound() -> None:
    data = minimal_screening()
    data["limit"] = 1000
    assert validate_screening(data).limit == 1000


@pytest.mark.parametrize("field", ["schemaVersion", "name", "market", "symbolTypes", "columns", "limit"])
def test_required_screening_field(field: str) -> None:
    data = minimal_screening()
    del data[field]
    with pytest.raises(ConfigError) as caught:
        validate_screening(data)
    assert caught.value.code == "CONFIG_VALIDATION_ERROR"


@pytest.mark.parametrize(
    "filters",
    [
        {"close": [None, None]},
        {"close": [10, 5]},
        {"close": [1]},
        {"close": [1, 2, 3]},
        {"close": True},
        {"close": [True, 5]},
        {"close": ["1", 5]},
        {"close": [float("inf"), 5]},
        {"close": [float("nan"), 5]},
        {" ": [1, 5]},
    ],
)
def test_invalid_filters(filters: object) -> None:
    data = minimal_screening()
    data["filters"] = filters
    with pytest.raises(ConfigError) as caught:
        validate_screening(data)
    assert caught.value.code == "CONFIG_VALIDATION_ERROR"


@pytest.mark.parametrize(
    "watchlist",
    [
        {"enabled": True},
        {"enabled": True, "name": " "},
        {"enabled": 1, "name": "Test"},
    ],
)
def test_invalid_watchlist(watchlist: dict) -> None:
    data = minimal_screening()
    data["watchlist"] = watchlist
    with pytest.raises(ConfigError):
        validate_screening(data)


def test_disabled_watchlist_without_name() -> None:
    data = minimal_screening()
    data["watchlist"] = {"enabled": False}
    assert validate_screening(data).watchlist.name is None


def test_load_screening_file(tmp_path: Path) -> None:
    path = tmp_path / "test_screen.json"
    path.write_text(json.dumps(minimal_screening()), encoding="utf-8")
    assert load_screening(path).name == "test_screen"
