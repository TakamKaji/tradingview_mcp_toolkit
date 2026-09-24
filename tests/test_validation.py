from __future__ import annotations

import json
from pathlib import Path

import pytest
from test_jobs import minimal_job
from test_screening import minimal_screening

from tradingview_screening.common.errors import ConfigError
from tradingview_screening.jobs.loader import (
    load_job,
    load_job_by_name,
    validate_job,
    validate_job_screening_reference,
)
from tradingview_screening.screening.validators import load_screening, load_screening_by_name


@pytest.mark.parametrize("loader", [load_job, load_screening])
def test_file_not_found(loader, tmp_path: Path) -> None:
    with pytest.raises(ConfigError) as caught:
        loader(tmp_path / "absent.json")
    assert caught.value.to_dict()["code"] == "CONFIG_FILE_NOT_FOUND"


@pytest.mark.parametrize("loader", [load_job, load_screening])
def test_malformed_json(loader, tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{oops", encoding="utf-8")
    with pytest.raises(ConfigError) as caught:
        loader(path)
    assert caught.value.to_dict()["code"] == "CONFIG_JSON_INVALID"
    assert "oops" not in caught.value.message


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
@pytest.mark.parametrize("loader", [load_job, load_screening])
def test_nonstandard_json_constant_rejected(loader, constant: str, tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text(f'{{"value": {constant}}}', encoding="utf-8")
    with pytest.raises(ConfigError) as caught:
        loader(path)
    assert caught.value.code == "CONFIG_JSON_INVALID"


def test_invalid_utf8(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_bytes(b"\xff")
    with pytest.raises(ConfigError) as caught:
        load_screening(path)
    assert caught.value.code == "CONFIG_JSON_INVALID"


def test_model_error_normalized(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({**minimal_screening(), "limit": 0}), encoding="utf-8")
    with pytest.raises(ConfigError) as caught:
        load_screening(path)
    assert caught.value.to_dict() == {
        "code": "CONFIG_VALIDATION_ERROR",
        "message": "Invalid screening definition",
        "field": "limit",
    }
    assert capsys.readouterr() == ("", "")


@pytest.mark.parametrize("name", ["../secret", "foo/bar", r"C:\temp\job", "CON", "foo.json", "a:b", "..", ""])
@pytest.mark.parametrize("loader", [load_job_by_name, load_screening_by_name])
def test_name_escape_rejected(loader, name: str, tmp_path: Path) -> None:
    with pytest.raises(ConfigError) as caught:
        loader(name, tmp_path)
    assert caught.value.code == "CONFIG_NAME_INVALID"


def test_symlink_escape_rejected(tmp_path: Path) -> None:
    directory = tmp_path / "screenings"
    directory.mkdir()
    outside = tmp_path / "outside.json"
    outside.write_text(json.dumps(minimal_screening()), encoding="utf-8")
    try:
        (directory / "alias.json").symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("Creating symlinks is unavailable")
    with pytest.raises(ConfigError) as caught:
        load_screening_by_name("alias", tmp_path)
    assert caught.value.code == "CONFIG_NAME_INVALID"


def test_resolved_file_escape_rejected_without_symlink_rights(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tradingview_screening.common import config

    directory = tmp_path / "screenings"
    directory.mkdir()
    original_resolve = Path.resolve

    def escape(self: Path, *args, **kwargs) -> Path:
        if self.name == "alias.json":
            return tmp_path.parent / "outside.json"
        return original_resolve(self, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", escape)
    with pytest.raises(ConfigError) as caught:
        config.definition_path(directory, "alias", project_root=tmp_path)
    assert caught.value.code == "CONFIG_NAME_INVALID"


def test_resolved_directory_escape_rejected_without_symlink_rights(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tradingview_screening.common import config

    directory = tmp_path / "screenings"
    original_resolve = Path.resolve

    def escape(self: Path, *args, **kwargs) -> Path:
        if self == directory:
            return tmp_path.parent / "outside"
        return original_resolve(self, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", escape)
    with pytest.raises(ConfigError) as caught:
        config.definition_path(directory, "alias", project_root=tmp_path)
    assert caught.value.code == "CONFIG_NAME_INVALID"


def test_job_screening_reference_success(tmp_path: Path) -> None:
    (tmp_path / "jobs").mkdir()
    (tmp_path / "screenings").mkdir()
    (tmp_path / "jobs" / "test_job.json").write_text(json.dumps(minimal_job()), encoding="utf-8")
    (tmp_path / "screenings" / "test_screen.json").write_text(
        json.dumps(minimal_screening()), encoding="utf-8"
    )
    job = load_job_by_name("test_job", tmp_path)
    assert validate_job_screening_reference(job, tmp_path).name == "test_screen"


def test_job_screening_reference_missing(tmp_path: Path) -> None:
    job = load_job_data(minimal_job())
    with pytest.raises(ConfigError) as caught:
        validate_job_screening_reference(job, tmp_path)
    assert caught.value.code == "CONFIG_REFERENCE_NOT_FOUND"


def test_job_screening_reference_traversal(tmp_path: Path) -> None:
    data = minimal_job()
    data["task"]["definition"] = "../secret"
    with pytest.raises(ConfigError) as caught:
        validate_job_screening_reference(load_job_data(data), tmp_path)
    assert caught.value.code == "CONFIG_NAME_INVALID"


@pytest.mark.parametrize(
    ("content", "expected_code"),
    [("{bad", "CONFIG_JSON_INVALID"), (json.dumps({"schemaVersion": 1}), "CONFIG_VALIDATION_ERROR")],
)
def test_job_screening_reference_invalid(content: str, expected_code: str, tmp_path: Path) -> None:
    directory = tmp_path / "screenings"
    directory.mkdir()
    (directory / "test_screen.json").write_text(content, encoding="utf-8")
    job = load_job_data(minimal_job())
    with pytest.raises(ConfigError) as caught:
        validate_job_screening_reference(job, tmp_path)
    assert caught.value.code == expected_code


def test_builtin_has_no_screening_reference(tmp_path: Path) -> None:
    data = minimal_job()
    data["task"] = {"type": "builtin", "definition": "us_sector_daily"}
    assert validate_job_screening_reference(load_job_data(data), tmp_path) is None


def load_job_data(data: dict):
    return validate_job(data)
