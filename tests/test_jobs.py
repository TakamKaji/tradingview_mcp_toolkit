from __future__ import annotations

from pathlib import Path

import pytest

from tradingview_screening.common.errors import ConfigError
from tradingview_screening.jobs.loader import load_job, validate_job


def minimal_job() -> dict:
    return {
        "schemaVersion": 1,
        "name": "test_job",
        "enabled": True,
        "task": {"type": "screening", "definition": "test_screen"},
        "schedule": {"type": "daily", "time": "15:40", "timezone": "Asia/Tokyo"},
        "output": {"save": True, "watchlistSync": False},
    }


def test_valid_screening_job() -> None:
    assert validate_job(minimal_job()).task.definition == "test_screen"


def test_valid_builtin_job() -> None:
    data = minimal_job()
    data["task"] = {"type": "builtin", "definition": "us_sector_daily"}
    assert validate_job(data).task.definition == "us_sector_daily"


def test_sample_job() -> None:
    path = Path(__file__).resolve().parents[1] / "jobs" / "sample_screen_daily.json"
    assert load_job(path).task.definition == "sample_standard_screen"


@pytest.mark.parametrize(
    ("location", "field", "value"),
    [
        ("root", "schemaVersion", 2),
        ("root", "schemaVersion", True),
        ("root", "schemaVersion", 1.0),
        ("root", "name", " "),
        ("root", "enabled", 1),
        ("task", "type", "unknown"),
        ("task", "definition", None),
        ("task", "definition", " "),
        ("schedule", "type", "weekly"),
        ("schedule", "time", "7:40"),
        ("schedule", "time", "24:00"),
        ("schedule", "time", "12:60"),
        ("schedule", "timezone", "Mars/Phobos"),
        ("schedule", "timezone", ""),
        ("output", "save", 1),
        ("output", "watchlistSync", "yes"),
    ],
)
def test_invalid_job_field(location: str, field: str, value: object) -> None:
    data = minimal_job()
    target = data if location == "root" else data[location]
    target[field] = value
    with pytest.raises(ConfigError) as caught:
        validate_job(data)
    assert caught.value.code == "CONFIG_VALIDATION_ERROR"


@pytest.mark.parametrize("location", ["root", "task", "schedule", "output"])
def test_unknown_job_key(location: str) -> None:
    data = minimal_job()
    target = data if location == "root" else data[location]
    target["other"] = True
    with pytest.raises(ConfigError, match="Invalid job definition"):
        validate_job(data)


def test_timezone_is_required() -> None:
    data = minimal_job()
    del data["schedule"]["timezone"]
    with pytest.raises(ConfigError) as caught:
        validate_job(data)
    assert caught.value.field == "schedule.timezone"


def test_latest_daily_time() -> None:
    data = minimal_job()
    data["schedule"]["time"] = "23:59"
    assert validate_job(data).schedule.time == "23:59"


@pytest.mark.parametrize("location,field", [("root", "schemaVersion"), ("root", "name"), ("task", "definition")])
def test_required_job_field(location: str, field: str) -> None:
    data = minimal_job()
    target = data if location == "root" else data[location]
    del target[field]
    with pytest.raises(ConfigError) as caught:
        validate_job(data)
    assert caught.value.code == "CONFIG_VALIDATION_ERROR"
