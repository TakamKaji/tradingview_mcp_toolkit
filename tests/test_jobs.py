from __future__ import annotations

from pathlib import Path

import pytest

from tradingview_screening.common.errors import ConfigError
from tradingview_screening.jobs.loader import list_job_names, load_job, load_job_by_name, validate_job


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


def test_load_job_by_name_requires_filename_match(tmp_path: Path) -> None:
    jobs = tmp_path / "jobs"
    jobs.mkdir()
    payload = minimal_job()
    payload["name"] = "different_name"
    (jobs / "test_job.json").write_text(
        __import__("json").dumps(payload),
        encoding="utf-8",
    )
    with pytest.raises(ConfigError) as caught:
        load_job_by_name("test_job", tmp_path)
    assert caught.value.code == "CONFIG_VALIDATION_ERROR"
    assert caught.value.field == "name"


def test_load_job_by_name_accepts_matching_name(tmp_path: Path) -> None:
    jobs = tmp_path / "jobs"
    jobs.mkdir()
    (jobs / "test_job.json").write_text(
        __import__("json").dumps(minimal_job()),
        encoding="utf-8",
    )
    assert load_job_by_name("test_job", tmp_path).name == "test_job"


def test_list_job_names_is_sorted_and_ignores_non_json(tmp_path: Path) -> None:
    jobs = tmp_path / "jobs"
    jobs.mkdir()
    for name in ("zeta", "alpha"):
        payload = minimal_job()
        payload["name"] = name
        (jobs / f"{name}.json").write_text(__import__("json").dumps(payload), encoding="utf-8")
    (jobs / "notes.txt").write_text("ignored", encoding="utf-8")
    assert list_job_names(tmp_path) == ("alpha", "zeta")


def test_list_job_names_missing_directory_is_empty(tmp_path: Path) -> None:
    assert list_job_names(tmp_path) == ()


def test_list_job_names_rejects_symlink_json_when_supported(tmp_path: Path) -> None:
    jobs = tmp_path / "jobs"
    jobs.mkdir()
    target = tmp_path / "outside.json"
    target.write_text(__import__("json").dumps(minimal_job()), encoding="utf-8")
    link = jobs / "linked.json"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("Creating symlinks is unavailable")
    with pytest.raises(ConfigError) as caught:
        list_job_names(tmp_path)
    assert caught.value.code == "CONFIG_NAME_INVALID"
