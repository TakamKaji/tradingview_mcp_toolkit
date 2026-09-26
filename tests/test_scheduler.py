from __future__ import annotations

import base64
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pytest

from tradingview_screening.common.errors import AppError, ConfigError
from tradingview_screening.jobs import scheduler


def make_job(
    root: Path, *, name: str = "daily", enabled: bool = True,
    timezone: str = "Asia/Tokyo", builtin: bool = False,
) -> None:
    (root / "jobs").mkdir(exist_ok=True)
    (root / "app.bat").write_text("@echo off\n", encoding="utf-8")
    (root / "jobs" / f"{name}.json").write_text(json.dumps({
        "schemaVersion": 1, "name": name, "enabled": enabled,
        "task": {"type": "builtin" if builtin else "screening", "definition": "sample"},
        "schedule": {"type": "daily", "time": "15:40", "timezone": timezone},
        "output": {"save": False, "watchlistSync": False},
    }), encoding="utf-8")
    if not builtin:
        (root / "screenings").mkdir(exist_ok=True)
        sample = Path(__file__).resolve().parents[1] / "screenings" / "sample_standard_screen.json"
        definition = json.loads(sample.read_text(encoding="utf-8"))
        definition["name"] = "sample"
        (root / "screenings" / "sample.json").write_text(
            json.dumps(definition), encoding="utf-8"
        )


def fake_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(scheduler.platform, "system", lambda: "Windows")
    monkeypatch.setattr(scheduler, "_powershell_path", lambda: r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe")


def test_apply_creates_and_reapplies_without_delete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    make_job(tmp_path)
    fake_windows(monkeypatch)
    requests: list[dict[str, Any]] = []
    def bridge(request: dict[str, Any]) -> dict:
        requests.append(request)
        return {"ok": True, "result": "created" if len(requests) == 1 else "updated"}
    monkeypatch.setattr(scheduler, "_bridge", bridge)
    first = scheduler.apply_schedules(tmp_path)
    second = scheduler.apply_schedules(tmp_path)
    assert [first["items"][0]["result"], second["items"][0]["result"]] == ["created", "updated"]
    assert [call["command"] for call in requests] == ["apply", "apply"]
    assert requests[0]["startBoundary"].endswith("+09:00")
    assert requests[0]["name"] == "daily"
    assert requests[0]["projectRoot"] == str(tmp_path.resolve())


def test_disabled_is_skipped_without_deleting_task(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    make_job(tmp_path, enabled=False)
    fake_windows(monkeypatch)
    monkeypatch.setattr(scheduler, "_bridge", lambda _request: pytest.fail("No Task write"))
    result = scheduler.apply_schedules(tmp_path)
    assert result["items"][0]["result"] == "skipped"
    assert result["items"][0]["reason"] == "disabled"


def test_removed_job_is_not_auto_deleted_by_apply(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    make_job(tmp_path)
    (tmp_path / "jobs" / "daily.json").unlink()
    fake_windows(monkeypatch)
    monkeypatch.setattr(scheduler, "_bridge", lambda _request: pytest.fail("No Task delete"))
    result = scheduler.apply_schedules(tmp_path)
    assert result["status"] == "success"
    assert result["items"] == []


@pytest.mark.parametrize("timezone", ["America/New_York", "Europe/London", "UTC"])
def test_unsupported_timezone_fails_before_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, timezone: str,
) -> None:
    make_job(tmp_path, timezone=timezone)
    fake_windows(monkeypatch)
    monkeypatch.setattr(scheduler, "_bridge", lambda _request: pytest.fail("No Task write"))
    with pytest.raises(AppError) as caught:
        scheduler.apply_schedules(tmp_path)
    assert caught.value.code == "SCHEDULE_TIMEZONE_UNSUPPORTED"


def test_builtin_enabled_is_rejected_before_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    make_job(tmp_path, builtin=True)
    fake_windows(monkeypatch)
    monkeypatch.setattr(scheduler, "_bridge", lambda _request: pytest.fail("No Task write"))
    with pytest.raises(AppError) as caught:
        scheduler.apply_schedules(tmp_path)
    assert caught.value.code == "JOB_TASK_UNAVAILABLE"


def test_apply_validates_all_jobs_before_any_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    make_job(tmp_path, name="alpha")
    make_job(tmp_path, name="zeta", timezone="America/New_York")
    fake_windows(monkeypatch)
    monkeypatch.setattr(scheduler, "_bridge", lambda _request: pytest.fail("No Task write"))
    with pytest.raises(AppError, match="timezone"):
        scheduler.apply_schedules(tmp_path)


def test_apply_partial_failure_keeps_completed_items(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    make_job(tmp_path, name="alpha")
    make_job(tmp_path, name="zeta")
    fake_windows(monkeypatch)
    calls: list[str] = []
    def bridge(request: dict) -> dict:
        calls.append(request["name"])
        if request["name"] == "zeta":
            raise AppError("SCHEDULE_OPERATION_ERROR", "Task registration failed")
        return {"ok": True, "result": "created"}
    monkeypatch.setattr(scheduler, "_bridge", bridge)
    result = scheduler.apply_schedules(tmp_path)
    assert result["status"] == "failed"
    assert [item["jobName"] for item in result["items"]] == ["alpha", "zeta"]
    assert result["items"][1]["result"] == "failed"
    assert result["items"][1]["error"]["code"] == "SCHEDULE_OPERATION_ERROR"
    assert calls == ["alpha", "zeta"]
    assert result["errors"][0]["code"] == "SCHEDULE_OPERATION_ERROR"


def test_remove_exact_without_job_definition(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_windows(monkeypatch)
    requests: list[dict] = []
    def bridge(request: dict) -> dict:
        requests.append(request)
        return {"ok": True, "removed": len(requests) == 1}
    monkeypatch.setattr(scheduler, "_bridge", bridge)
    first = scheduler.remove_schedule("old_job", tmp_path)
    second = scheduler.remove_schedule("old_job", tmp_path)
    assert first["removed"] is True
    assert second["removed"] is False
    assert requests == [{"command": "remove", "name": "old_job"}] * 2
    assert first["taskName"] == "TradingViewMcpSupport__old_job"
    with pytest.raises(ConfigError):
        scheduler.remove_schedule("../other", tmp_path)


def test_list_filters_nonprefix_and_sorts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_windows(monkeypatch)
    monkeypatch.setattr(scheduler, "_bridge", lambda _request: {"ok": True, "items": [
        {"taskName": "Unrelated", "enabled": True},
        {"taskName": "TradingViewMcpSupport__zeta", "enabled": False},
        {"taskName": "TradingViewMcpSupport__alpha", "enabled": True},
    ]})
    result = scheduler.list_schedules(tmp_path)
    assert [task["jobName"] for task in result["tasks"]] == ["alpha", "zeta"]


def test_nonwindows_is_unsupported(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    make_job(tmp_path)
    monkeypatch.setattr(scheduler.platform, "system", lambda: "Linux")
    with pytest.raises(AppError) as caught:
        scheduler.apply_schedules(tmp_path)
    assert caught.value.code == "SCHEDULE_UNSUPPORTED"
    with pytest.raises(AppError) as caught:
        scheduler.list_schedules(tmp_path)
    assert caught.value.code == "SCHEDULE_UNSUPPORTED"
    with pytest.raises(AppError) as caught:
        scheduler.remove_schedule("daily", tmp_path)
    assert caught.value.code == "SCHEDULE_UNSUPPORTED"


def test_boundary_is_next_tokyo_occurrence() -> None:
    tokyo = ZoneInfo("Asia/Tokyo")
    before = datetime(2026, 9, 26, 15, 39, tzinfo=tokyo)
    after = datetime(2026, 9, 26, 15, 41, tzinfo=tokyo)
    assert scheduler._next_boundary("15:40", now=before) == "2026-09-26T15:40:00+09:00"
    assert scheduler._next_boundary("15:40", now=after) == "2026-09-27T15:40:00+09:00"


def test_path_with_spaces_and_encoded_action_is_data_only(tmp_path: Path) -> None:
    root = tmp_path / "project with spaces"
    root.mkdir()
    make_job(root)
    resolved, app = scheduler._safe_action_paths(root)
    action = scheduler._action_arguments(resolved, app, "daily")
    encoded = action.rsplit(" ", 1)[1]
    source = base64.b64decode(encoded).decode("utf-16-le")
    assert "-WindowStyle Hidden" in action
    assert "CreateNoWindow = $true" in source
    assert "UseShellExecute = $false" in source
    assert "WaitForExit()" in source
    assert resolved not in source
    assert app not in source
    assert "daily" not in source
    encoded_json = source.split("FromBase64String('", 1)[1].split("')", 1)[0]
    assert json.loads(base64.b64decode(encoded_json)) == {
        "projectRoot": resolved, "appBat": app, "name": "daily",
    }


def test_unsafe_repo_path_is_rejected_before_action(tmp_path: Path) -> None:
    root = tmp_path / "unsafe&path"
    root.mkdir()
    (root / "app.bat").write_text("@echo off\n", encoding="utf-8")
    with pytest.raises(ConfigError):
        scheduler._safe_action_paths(root)


def test_bridge_uses_absolute_executable_and_json_stdin(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_windows(monkeypatch)
    captured: dict[str, Any] = {}
    def run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        captured["command"] = command
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(command, 0, '{"ok":true,"removed":false}', "")
    monkeypatch.setattr(scheduler.subprocess, "run", run)
    answer = scheduler._bridge({"command": "remove", "name": "daily"})
    assert answer["removed"] is False
    assert captured["command"][0].endswith(r"WindowsPowerShell\v1.0\powershell.exe")
    assert captured["command"][1:3] == ["-NoProfile", "-NonInteractive"]
    assert json.loads(captured["kwargs"]["input"]) == {"command": "remove", "name": "daily"}
    assert captured["kwargs"]["encoding"] == "utf-8"
    assert "daily" not in " ".join(captured["command"])


def test_bridge_timeout_and_conflict(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_windows(monkeypatch)
    def timed_out(*_args: object, **_kwargs: object) -> None:
        raise subprocess.TimeoutExpired("powershell.exe", 30)
    monkeypatch.setattr(scheduler.subprocess, "run", timed_out)
    with pytest.raises(AppError) as caught:
        scheduler._bridge({"command": "list"})
    assert caught.value.code == "SCHEDULE_TIMEOUT"
    monkeypatch.setattr(
        scheduler.subprocess, "run",
        lambda command, **_kwargs: subprocess.CompletedProcess(
            command, 0, '{"ok":false,"code":"SCHEDULE_TASK_NAME_CONFLICT"}', ""
        ),
    )
    with pytest.raises(AppError) as caught:
        scheduler._bridge({"command": "remove", "name": "daily"})
    assert caught.value.code == "SCHEDULE_TASK_NAME_CONFLICT"


@pytest.mark.parametrize(
    ("returncode", "stdout", "expected_code"),
    [
        (1, "", "SCHEDULE_OPERATION_ERROR"),
        (0, "not JSON", "SCHEDULE_OPERATION_ERROR"),
        (0, '{"ok":false,"code":"SCHEDULE_ACCOUNT_ERROR","secret":"private"}', "SCHEDULE_OPERATION_ERROR"),
    ],
)
def test_bridge_failure_is_secret_free_app_error(
    monkeypatch: pytest.MonkeyPatch, returncode: int, stdout: str, expected_code: str,
) -> None:
    fake_windows(monkeypatch)
    monkeypatch.setattr(
        scheduler.subprocess, "run",
        lambda command, **_kwargs: subprocess.CompletedProcess(
            command, returncode, stdout, "token=private"
        ),
    )
    with pytest.raises(AppError) as caught:
        scheduler._bridge({"command": "remove", "name": "daily"})
    assert caught.value.code == expected_code
    assert "private" not in caught.value.message
    assert "token" not in caught.value.message


def test_bridge_process_start_failure_is_app_error(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_windows(monkeypatch)
    def missing_executable(*_args: object, **_kwargs: object) -> None:
        raise OSError("secret path")
    monkeypatch.setattr(scheduler.subprocess, "run", missing_executable)
    with pytest.raises(AppError) as caught:
        scheduler._bridge({"command": "list"})
    assert caught.value.code == "SCHEDULE_OPERATION_ERROR"
    assert "secret" not in caught.value.message


def test_bridge_does_not_misclassify_account_error_as_missing() -> None:
    assert "-2147024894" in scheduler._COM_SCRIPT
    assert "-2147216625" not in scheduler._COM_SCRIPT
    assert "OrdinalIgnoreCase" in scheduler._COM_SCRIPT
    assert "SCHEDULE_TASK_NAME_CONFLICT" in scheduler._COM_SCRIPT
