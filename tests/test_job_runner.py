from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path
from typing import Self

import pytest

from tradingview_screening.common.errors import AppError, ConfigError
from tradingview_screening.jobs import runner


def root_with_job(
    tmp_path: Path, *, name: str = "daily", enabled: bool = True,
    save: bool = False, sync: bool = False, builtin: bool = False,
) -> Path:
    jobs = tmp_path / "jobs"
    jobs.mkdir(exist_ok=True)
    (jobs / f"{name}.json").write_text(json.dumps({
        "schemaVersion": 1, "name": name, "enabled": enabled,
        "task": {"type": "builtin" if builtin else "screening", "definition": "sample"},
        "schedule": {"type": "daily", "time": "15:40", "timezone": "Asia/Tokyo"},
        "output": {"save": save, "watchlistSync": sync},
    }), encoding="utf-8")
    if not builtin:
        screenings = tmp_path / "screenings"
        screenings.mkdir(exist_ok=True)
        sample = Path(__file__).resolve().parents[1] / "screenings" / "sample_standard_screen.json"
        definition = json.loads(sample.read_text(encoding="utf-8"))
        definition["name"] = "sample"
        (screenings / "sample.json").write_text(json.dumps(definition), encoding="utf-8")
    return tmp_path


def screening_result(*, status: str = "success") -> dict:
    errors = [] if status == "success" else [{"code": "SOURCE_ERROR", "message": "Source failed"}]
    rows = [{"symbol": "TSE:7203", "name": "Example"}] if status != "failed" else []
    return {
        "schemaVersion": 1, "status": status, "operation": "screening", "name": "sample",
        "executedAt": "2026-09-26T15:00:00+09:00", "source": "tradingview_official_mcp",
        "metadata": {
            "requestedCount": 1, "returnedCount": len(rows),
            "partial": status == "partial", "durationMs": 1,
        },
        "results": rows, "errors": errors,
    }


class FakeClient:
    entered = 0
    exited = 0
    enter_error: AppError | None = None

    async def __aenter__(self) -> Self:
        if self.enter_error:
            raise self.enter_error
        FakeClient.entered += 1
        return self

    async def __aexit__(self, *_args: object) -> None:
        FakeClient.exited += 1


@pytest.fixture(autouse=True)
def reset_fake_client() -> None:
    FakeClient.entered = 0
    FakeClient.exited = 0
    FakeClient.enter_error = None


@pytest.mark.parametrize("save,sync", [(False, False), (True, False), (False, True), (True, True)])
def test_job_options_and_same_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, save: bool, sync: bool,
) -> None:
    root = root_with_job(tmp_path, save=save, sync=sync, enabled=False)
    seen: list[tuple[str, object]] = []
    monkeypatch.setattr(runner, "TradingViewClient", FakeClient)

    async def fake_screen(_screening: object, client: object) -> dict:
        seen.append(("screen", client))
        return screening_result()

    def fake_save(_result: dict, project_root: Path) -> Path:
        seen.append(("save", project_root))
        return project_root / "results" / "saved.json"

    async def fake_sync(_screening: object, _result: dict, client: object, _root: Path) -> dict:
        seen.append(("sync", client))
        return {"status": "success", "errors": []}

    monkeypatch.setattr(runner, "run_screening", fake_screen)
    monkeypatch.setattr(runner, "save_result", fake_save)
    monkeypatch.setattr(runner, "sync_screening_watchlist", fake_sync)
    payload = asyncio.run(runner.run_job("daily", root))
    assert payload["status"] == "success"
    assert payload["operation"] == "job"
    assert payload["metadata"]["saved"] is save
    assert payload["metadata"]["resultPath"] == ("results/saved.json" if save else None)
    assert payload["watchlistSync"] == ({"status": "success", "errors": []} if sync else None)
    assert [step for step, _ in seen] == ["screen"] + (["save"] if save else []) + (["sync"] if sync else [])
    if sync:
        assert seen[0][1] is seen[-1][1]
    assert FakeClient.entered == FakeClient.exited == 1
    assert runner.job_exit_code(payload) == 0


def test_partial_screening_saves_but_skips_sync(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = root_with_job(tmp_path, save=True, sync=True)
    monkeypatch.setattr(runner, "TradingViewClient", FakeClient)

    async def partial(_screening: object, _client: object) -> dict:
        return screening_result(status="partial")

    monkeypatch.setattr(runner, "run_screening", partial)
    monkeypatch.setattr(runner, "save_result", lambda _result, project_root: project_root / "saved.json")
    async def forbidden(*_args: object) -> dict:
        pytest.fail("Partial screening must not sync a Watchlist")
    monkeypatch.setattr(runner, "sync_screening_watchlist", forbidden)
    payload = asyncio.run(runner.run_job("daily", root))
    assert payload["status"] == "partial"
    assert payload["metadata"]["saved"] is True
    assert payload["watchlistSync"] == {
        "status": "skipped", "reason": "screening_not_successful",
    }
    assert runner.job_exit_code(payload) == 0


def test_failed_screening_does_not_save_or_sync(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = root_with_job(tmp_path, save=True, sync=True)
    monkeypatch.setattr(runner, "TradingViewClient", FakeClient)
    async def failed(_screening: object, _client: object) -> dict:
        return screening_result(status="failed")
    monkeypatch.setattr(runner, "run_screening", failed)
    monkeypatch.setattr(runner, "save_result", lambda *_args: pytest.fail("Must not save failed result"))
    payload = asyncio.run(runner.run_job("daily", root))
    assert payload["status"] == "failed"
    assert payload["metadata"]["saved"] is False
    assert payload["watchlistSync"]["status"] == "skipped"
    assert runner.job_exit_code(payload) == 1


def test_save_failure_prevents_write(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = root_with_job(tmp_path, save=True, sync=True)
    monkeypatch.setattr(runner, "TradingViewClient", FakeClient)
    async def success(_screening: object, _client: object) -> dict:
        return screening_result()
    monkeypatch.setattr(runner, "run_screening", success)
    def fail_save(*_args: object) -> Path:
        raise AppError("RESULT_WRITE_ERROR", "Cannot save result")
    async def forbidden(*_args: object) -> dict:
        pytest.fail("Save failure must prevent Watchlist Write")
    monkeypatch.setattr(runner, "save_result", fail_save)
    monkeypatch.setattr(runner, "sync_screening_watchlist", forbidden)
    payload = asyncio.run(runner.run_job("daily", root))
    assert payload["status"] == "failed"
    assert payload["metadata"]["saved"] is False
    assert payload["errors"][0]["code"] == "RESULT_WRITE_ERROR"


def test_sync_partial_auth_still_exits_three(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = root_with_job(tmp_path, sync=True)
    monkeypatch.setattr(runner, "TradingViewClient", FakeClient)
    async def success(_screening: object, _client: object) -> dict:
        return screening_result()
    async def partial(*_args: object) -> dict:
        return {"status": "partial", "errors": [{"code": "AUTH_REQUIRED", "message": "Auth needed"}]}
    monkeypatch.setattr(runner, "run_screening", success)
    monkeypatch.setattr(runner, "sync_screening_watchlist", partial)
    payload = asyncio.run(runner.run_job("daily", root))
    assert payload["status"] == "partial"
    assert runner.job_exit_code(payload) == 3


def test_sync_failed_preserves_saved_result_and_exits_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = root_with_job(tmp_path, save=True, sync=True)
    monkeypatch.setattr(runner, "TradingViewClient", FakeClient)
    async def success(_screening: object, _client: object) -> dict:
        return screening_result()
    async def failed_sync(*_args: object) -> dict:
        return {
            "status": "failed",
            "errors": [{"code": "WATCHLIST_WRITE_UNCONFIRMED", "message": "Write unknown"}],
        }
    monkeypatch.setattr(runner, "run_screening", success)
    monkeypatch.setattr(runner, "save_result", lambda _result, project_root: project_root / "saved.json")
    monkeypatch.setattr(runner, "sync_screening_watchlist", failed_sync)
    payload = asyncio.run(runner.run_job("daily", root))
    assert payload["status"] == "failed"
    assert payload["metadata"]["saved"] is True
    assert payload["metadata"]["resultPath"] == "saved.json"
    assert payload["watchlistSync"]["status"] == "failed"
    assert payload["errors"][0]["code"] == "WATCHLIST_WRITE_UNCONFIRMED"
    assert runner.job_exit_code(payload) == 1


def test_builtin_unavailable_without_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = root_with_job(tmp_path, builtin=True)
    monkeypatch.setattr(runner, "TradingViewClient", FakeClient)
    payload = asyncio.run(runner.run_job("daily", root))
    assert payload["status"] == "failed"
    assert payload["errors"][0]["code"] == "JOB_TASK_UNAVAILABLE"
    assert runner.job_exit_code(payload) == 1
    assert FakeClient.entered == 0


def test_auth_required_without_browser(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = root_with_job(tmp_path)
    monkeypatch.setattr(runner, "TradingViewClient", FakeClient)
    FakeClient.enter_error = AppError("AUTH_REQUIRED", "TradingView authorization is required")
    payload = asyncio.run(runner.run_job("daily", root))
    assert payload["errors"][0]["code"] == "AUTH_REQUIRED"
    assert runner.job_exit_code(payload) == 3


def test_reference_missing_is_config_error(tmp_path: Path) -> None:
    root = root_with_job(tmp_path)
    (root / "screenings" / "sample.json").unlink()
    payload = asyncio.run(runner.run_job("daily", root))
    assert payload["status"] == "failed"
    assert payload["errors"][0]["code"] == "CONFIG_REFERENCE_NOT_FOUND"
    assert runner.job_exit_code(payload) == 2


def test_missing_job_is_load_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigError) as caught:
        asyncio.run(runner.run_job("missing", tmp_path))
    assert caught.value.code == "CONFIG_FILE_NOT_FOUND"


def test_lock_is_hashed_and_same_job_skips(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = root_with_job(tmp_path)
    path = runner._lock_path(root, "daily")
    assert path.name == hashlib.sha256(b"daily").hexdigest() + ".lock"
    assert "daily" not in path.name
    monkeypatch.setattr(runner, "TradingViewClient", FakeClient)
    entered = asyncio.Event()
    finish = asyncio.Event()
    async def held(_screening: object, _client: object) -> dict:
        entered.set()
        await finish.wait()
        return screening_result()
    monkeypatch.setattr(runner, "run_screening", held)
    async def exercise() -> tuple[dict, dict]:
        first = asyncio.create_task(runner.run_job("daily", root))
        await entered.wait()
        second = await runner.run_job("daily", root)
        finish.set()
        return await first, second
    first, second = asyncio.run(exercise())
    assert first["status"] == "success"
    assert second["metadata"]["reason"] == "already_running"
    assert runner.job_exit_code(second) == 0
    assert FakeClient.entered == 1


def test_different_jobs_run_independently(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = root_with_job(tmp_path)
    root_with_job(tmp_path, name="other")
    monkeypatch.setattr(runner, "TradingViewClient", FakeClient)
    waiting = asyncio.Event()
    release = asyncio.Event()
    async def held(_screening: object, _client: object) -> dict:
        waiting.set()
        await release.wait()
        return screening_result()
    monkeypatch.setattr(runner, "run_screening", held)
    async def exercise() -> tuple[dict, dict]:
        first = asyncio.create_task(runner.run_job("daily", root))
        await waiting.wait()
        second = asyncio.create_task(runner.run_job("other", root))
        await asyncio.sleep(0)
        assert FakeClient.entered == 2
        release.set()
        return await first, await second
    first, second = asyncio.run(exercise())
    assert first["status"] == second["status"] == "success"


def test_lock_covers_sync_and_releases_after_cancellation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = root_with_job(tmp_path, sync=True)
    monkeypatch.setattr(runner, "TradingViewClient", FakeClient)
    entered_sync = asyncio.Event()
    sync_calls = 0
    async def success(_screening: object, _client: object) -> dict:
        return screening_result()
    async def sync(*_args: object) -> dict:
        nonlocal sync_calls
        sync_calls += 1
        if sync_calls == 1:
            entered_sync.set()
            await asyncio.Event().wait()
        return {"status": "success", "errors": []}
    monkeypatch.setattr(runner, "run_screening", success)
    monkeypatch.setattr(runner, "sync_screening_watchlist", sync)
    async def exercise() -> tuple[dict, dict]:
        first = asyncio.create_task(runner.run_job("daily", root))
        await entered_sync.wait()
        duplicate = await runner.run_job("daily", root)
        first.cancel()
        with pytest.raises(asyncio.CancelledError):
            await first
        after_cancel = await runner.run_job("daily", root)
        return duplicate, after_cancel
    duplicate, after_cancel = asyncio.run(exercise())
    assert duplicate["metadata"]["reason"] == "already_running"
    assert runner.job_exit_code(duplicate) == 0
    assert after_cancel["status"] == "success"
    assert sync_calls == 2
    assert FakeClient.entered == FakeClient.exited == 2


def test_failure_releases_lock(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = root_with_job(tmp_path)
    monkeypatch.setattr(runner, "TradingViewClient", FakeClient)
    calls = 0
    async def sometimes(_screening: object, _client: object) -> dict:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise AppError("MCP_TOOL_ERROR", "Provider failed")
        return screening_result()
    monkeypatch.setattr(runner, "run_screening", sometimes)
    first = asyncio.run(runner.run_job("daily", root))
    second = asyncio.run(runner.run_job("daily", root))
    assert first["status"] == "failed"
    assert second["status"] == "success"


def test_lock_path_failure_is_not_already_running(tmp_path: Path) -> None:
    root = root_with_job(tmp_path)
    (root / ".local").write_text("not a directory", encoding="utf-8")
    with pytest.raises(AppError) as caught:
        asyncio.run(runner.run_job("daily", root))
    assert caught.value.code == "JOB_LOCK_ERROR"


def test_lock_release_failure_preserves_completed_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = root_with_job(tmp_path)
    monkeypatch.setattr(runner, "TradingViewClient", FakeClient)
    async def success(_screening: object, _client: object) -> dict:
        return screening_result()
    monkeypatch.setattr(runner, "run_screening", success)
    class BrokenRelease:
        def __init__(self, _path: Path, *, thread_local: bool) -> None:
            assert thread_local is False
        def acquire(self, *, timeout: int) -> None:
            assert timeout == 0
        def release(self) -> None:
            raise OSError("untrusted lock failure")
    monkeypatch.setattr(runner, "FileLock", BrokenRelease)
    payload = asyncio.run(runner.run_job("daily", root))
    assert payload["status"] == "failed"
    assert payload["screening"]["status"] == "success"
    assert payload["errors"][0]["code"] == "JOB_LOCK_ERROR"
    assert runner.job_exit_code(payload) == 1


def test_jobs_list_validates_references_and_orders(tmp_path: Path) -> None:
    root = root_with_job(tmp_path, name="zeta")
    root_with_job(tmp_path, name="alpha")
    names = [item["name"] for item in runner.list_jobs(root)["jobs"]]
    assert names == ["alpha", "zeta"]
    (root / "screenings" / "sample.json").unlink()
    with pytest.raises(ConfigError) as caught:
        runner.list_jobs(root)
    assert caught.value.code == "CONFIG_REFERENCE_NOT_FOUND"
