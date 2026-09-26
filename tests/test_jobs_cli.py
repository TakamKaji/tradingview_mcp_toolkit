from __future__ import annotations

import json

import pytest

from tradingview_screening import __main__ as cli
from tradingview_screening.common.errors import AppError, ConfigError


@pytest.mark.parametrize(
    ("status", "errors", "expected_exit"),
    [
        ("success", [], 0),
        ("partial", [{"code": "WATCHLIST_WRITE_UNCONFIRMED", "message": "Unknown"}], 0),
        ("partial", [{"code": "AUTH_REQUIRED", "message": "Auth needed"}], 3),
        ("failed", [{"code": "MCP_TOOL_ERROR", "message": "Provider failed"}], 1),
        ("failed", [{"code": "CONFIG_REFERENCE_NOT_FOUND", "message": "Missing"}], 2),
    ],
)
def test_run_cli_exit_and_one_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
    status: str, errors: list[dict], expected_exit: int,
) -> None:
    async def fake_run(name: str, _root: object) -> dict:
        assert name == "sample"
        return {
            "schemaVersion": 1, "status": status, "operation": "job", "name": name,
            "metadata": {"skipped": False}, "errors": errors,
        }
    monkeypatch.setattr(cli, "run_job", fake_run)
    assert cli.main(["run", "sample"]) == expected_exit
    output = capsys.readouterr()
    assert len(output.out.splitlines()) == 1
    assert json.loads(output.out)["status"] == status
    assert (output.err == "") is (expected_exit == 0)


def test_run_missing_definition_returns_job_envelope(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    async def missing(*_args: object) -> dict:
        raise ConfigError("CONFIG_FILE_NOT_FOUND", "Job definition not found")
    monkeypatch.setattr(cli, "run_job", missing)
    assert cli.main(["run", "missing"]) == 2
    output = capsys.readouterr()
    payload = json.loads(output.out)
    assert payload["operation"] == "job"
    assert payload["name"] == "missing"
    assert payload["errors"][0]["code"] == "CONFIG_FILE_NOT_FOUND"
    assert len(output.out.splitlines()) == 1


def test_jobs_list_invalid_is_exit_two(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    def invalid(_root: object) -> dict:
        raise ConfigError("CONFIG_JSON_INVALID", "Invalid job JSON")
    monkeypatch.setattr(cli, "list_jobs", invalid)
    assert cli.main(["jobs", "list"]) == 2
    output = capsys.readouterr()
    assert json.loads(output.out)["error"]["code"] == "CONFIG_JSON_INVALID"
    assert len(output.out.splitlines()) == 1


def test_jobs_list_success(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(cli, "list_jobs", lambda _root: {
        "schemaVersion": 1, "status": "success", "operation": "jobs_list", "jobs": [],
    })
    assert cli.main(["jobs", "list"]) == 0
    assert json.loads(capsys.readouterr().out)["jobs"] == []


@pytest.mark.parametrize(
    ("argv", "function", "operation"),
    [
        (["schedule", "apply"], "apply_schedules", "schedule_apply"),
        (["schedule", "list"], "list_schedules", "schedule_list"),
        (["schedule", "remove", "old"], "remove_schedule", "schedule_remove"),
    ],
)
def test_schedule_cli_success(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
    argv: list[str], function: str, operation: str,
) -> None:
    monkeypatch.setattr(cli, function, lambda *_args: {
        "schemaVersion": 1, "status": "success", "operation": operation, "errors": [],
    })
    assert cli.main(argv) == 0
    output = capsys.readouterr()
    assert len(output.out.splitlines()) == 1
    assert json.loads(output.out)["operation"] == operation
    assert output.err == ""


def test_schedule_apply_partial_failure_is_exit_one(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cli, "apply_schedules", lambda _root: {
        "schemaVersion": 1, "status": "failed", "operation": "schedule_apply",
        "items": [{"jobName": "first", "result": "created"}],
        "errors": [{"code": "SCHEDULE_OPERATION_ERROR", "message": "Task failed"}],
    })
    assert cli.main(["schedule", "apply"]) == 1
    output = capsys.readouterr()
    payload = json.loads(output.out)
    assert payload["items"][0]["jobName"] == "first"
    assert payload["errors"][0]["code"] == "SCHEDULE_OPERATION_ERROR"


@pytest.mark.parametrize("code", ["JOB_TASK_UNAVAILABLE", "SCHEDULE_TIMEZONE_UNSUPPORTED"])
def test_scheduler_unsupported_is_runtime_exit_one(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], code: str,
) -> None:
    def unsupported(_root: object) -> dict:
        raise AppError(code, "Unsupported operation")
    monkeypatch.setattr(cli, "apply_schedules", unsupported)
    assert cli.main(["schedule", "apply"]) == 1
    assert json.loads(capsys.readouterr().out)["error"]["code"] == code


@pytest.mark.parametrize("argv", [["run"], ["jobs"], ["schedule"], ["schedule", "remove"]])
def test_usage_exit_two(argv: list[str], capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(argv) == 2
    output = capsys.readouterr()
    assert len(output.out.splitlines()) == 1
    assert json.loads(output.out)["error"]["code"] == "CLI_USAGE_ERROR"
