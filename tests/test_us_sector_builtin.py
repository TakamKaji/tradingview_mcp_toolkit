from __future__ import annotations

import asyncio
import json
import math
from pathlib import Path
from typing import Any, Self

import pytest

from tradingview_screening.common.errors import AppError, ConfigError
from tradingview_screening.integrations.tradingview.schemas import (
    ObservedReadData,
    ObservedReadResponse,
)
from tradingview_screening.integrations.tradingview.us_sector_normalization import (
    normalize_us_sector_screener,
    require_sector_column,
)
from tradingview_screening.jobs import runner
from tradingview_screening.jobs.builtin import run_us_sector_daily
from tradingview_screening.screening.results import write_json_result


def response(content: dict[str, Any] | None, *, text: str = "ignored") -> ObservedReadResponse:
    return ObservedReadResponse.model_validate({
        "structured_content": content, "content": [{"type": "text", "text": text}],
    })


def catalog(name: str, *, markets: list[str] | None = None) -> ObservedReadResponse:
    return response({"success": True, "columns": [{
        "name": name, "markets": markets if markets is not None else ["stock"],
    }]})


def screener(rows: list[Any], total: Any) -> ObservedReadResponse:
    return response({"success": True, "data": {"rows": rows, "totalCount": total}})


@pytest.mark.parametrize("name", ["sector", "change"])
def test_field_discovery_accepts_stock_column(name: str) -> None:
    require_sector_column(catalog(name), name)


def test_field_discovery_selects_exact_name_from_both_columns() -> None:
    both = response({"success": True, "columns": [
        {"name": "sector", "markets": ["stock"]},
        {"name": "change", "markets": ["stock"]},
    ]})
    require_sector_column(both, "sector")
    require_sector_column(both, "change")


@pytest.mark.parametrize("content,name", [
    ({"success": True, "columns": []}, "sector"),
    ({"success": True, "columns": [{"name": "sector", "markets": ["crypto"]}]}, "sector"),
    ({"success": True}, "change"),
])
def test_field_discovery_rejects_missing_column(content: dict, name: str) -> None:
    with pytest.raises(AppError) as caught:
        require_sector_column(response(content), name)
    assert caught.value.code == "MCP_SCHEMA_MISMATCH"


def test_provider_business_failure_hides_raw_text() -> None:
    with pytest.raises(AppError) as caught:
        require_sector_column(response({"success": False, "error": "secret"}, text="secret"), "sector")
    assert caught.value.code == "PROVIDER_ERROR"
    assert "secret" not in caught.value.message


def test_valid_screener_rows_are_minimal() -> None:
    rows, total = normalize_us_sector_screener(screener([
        {"symbol": "NYSE:A", "sector": " Technology ", "change": 1.0, "secret": "hidden"},
        {"symbol": "NYSE:B", "change": None},
    ], 2))
    assert rows == [
        {"symbol": "NYSE:A", "sector": "Technology", "change": 1.0},
        {"symbol": "NYSE:B", "sector": None, "change": None},
    ]
    assert total == 2


@pytest.mark.parametrize("content", [
    {"success": True},
    {"success": True, "data": {"rows": [{"symbol": "A"}], "totalCount": True}},
    {"success": True, "data": {"rows": [{"symbol": "A"}], "totalCount": 0}},
    {"success": True, "data": {"rows": ["bad"], "totalCount": 1}},
    {"success": True, "data": {"rows": [{"symbol": " "}], "totalCount": 1}},
    {"success": True, "data": {"rows": [{"symbol": "A", "sector": 1}], "totalCount": 1}},
    {"success": True, "data": {"rows": [{"symbol": "A", "sector": None, "change": True}], "totalCount": 1}},
    {"success": True, "data": {"rows": [{"symbol": "A", "change": "1.0"}], "totalCount": 1}},
    {"success": True, "data": {"rows": [
        {"symbol": "A", "sector": None, "change": 1},
        {"symbol": "A", "sector": None, "change": 2},
    ], "totalCount": 2}},
])
def test_malformed_screener_is_schema_mismatch(content: dict) -> None:
    with pytest.raises(AppError) as caught:
        normalize_us_sector_screener(response(content))
    assert caught.value.code == "MCP_SCHEMA_MISMATCH"


def test_content_body_is_not_reparsed() -> None:
    with pytest.raises(AppError) as caught:
        normalize_us_sector_screener(response(None, text='{"success":true,"data":{"rows":[]}}'))
    assert caught.value.code == "MCP_SCHEMA_MISMATCH"


@pytest.mark.parametrize("invalid", [math.nan, math.inf, -math.inf])
def test_normalizer_defensively_rejects_nonfinite_change(invalid: float) -> None:
    content = ObservedReadData.model_construct(
        success=True, data={"rows": [{"symbol": "A", "change": invalid}], "totalCount": 1}
    )
    unchecked = ObservedReadResponse.model_construct(structured_content=content, content=[])
    with pytest.raises(AppError) as caught:
        normalize_us_sector_screener(unchecked)
    assert caught.value.code == "MCP_SCHEMA_MISMATCH"


class SectorClient:
    def __init__(self, rows: list[dict[str, Any]] | None = None, total: int = 1) -> None:
        self.rows = rows if rows is not None else [{"symbol": "NYSE:A", "sector": "Technology", "change": 1.5}]
        self.total = total
        self.requests: list[tuple[str, Any]] = []

    async def get_screener_columns(self, request: Any) -> ObservedReadResponse:
        self.requests.append(("discovery", request))
        return catalog(request.search)

    async def run_screener(self, request: Any) -> ObservedReadResponse:
        self.requests.append(("screener", request))
        return screener(self.rows, self.total)


def test_builtin_uses_same_client_and_exact_universe_request() -> None:
    client = SectorClient()
    result = asyncio.run(run_us_sector_daily(client))
    assert result["operation"] == "us_sector_summary"
    assert result["results"][0]["meanChange"] == 1.5
    assert [kind for kind, _ in client.requests] == ["discovery", "discovery", "screener"]
    request = client.requests[-1][1]
    assert request.market == "america"
    assert request.symbol_types == ["stock"]
    assert request.columns == ["sector", "change"]
    assert request.limit == 1000
    assert "filters" not in request.model_fields_set


@pytest.mark.parametrize("rows,total,code", [
    ([{"symbol": "A", "sector": "Technology", "change": 1}], 2, "US_SECTOR_COVERAGE_INCOMPLETE"),
    ([{"symbol": "A", "sector": "Technology", "change": 1}] * 2, 2, "US_SECTOR_COVERAGE_INCOMPLETE"),
    ([{"symbol": "A", "sector": "Technology", "change": 1},
      {"symbol": "A", "sector": "Technology", "change": 2}], 2, "MCP_SCHEMA_MISMATCH"),
])
def test_builtin_rejects_incomplete_or_conflicting_coverage(
    rows: list[dict[str, Any]], total: int, code: str,
) -> None:
    with pytest.raises(AppError) as caught:
        asyncio.run(run_us_sector_daily(SectorClient(rows, total)))
    assert caught.value.code == code


def make_job(root: Path, *, save: bool, sync: bool = False, definition: str = "us_sector_daily") -> None:
    (root / "jobs").mkdir(exist_ok=True)
    (root / "jobs" / "sector.json").write_text(json.dumps({
        "schemaVersion": 1, "name": "sector", "enabled": True,
        "task": {"type": "builtin", "definition": definition},
        "schedule": {"type": "daily", "time": "07:00", "timezone": "Asia/Tokyo"},
        "output": {"save": save, "watchlistSync": sync},
    }), encoding="utf-8")


class SessionClient(SectorClient):
    entered = 0

    async def __aenter__(self) -> Self:
        SessionClient.entered += 1
        return self

    async def __aexit__(self, *_args: object) -> None:
        SessionClient.entered -= 1


@pytest.mark.parametrize("save", [True, False])
def test_job_dispatch_and_save(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, save: bool) -> None:
    make_job(tmp_path, save=save)
    monkeypatch.setattr(runner, "TradingViewClient", SessionClient)
    result = asyncio.run(runner.run_job("sector", tmp_path))
    assert result["status"] == "success"
    assert result["builtin"]["operation"] == "us_sector_summary"
    assert result["screening"] is None
    assert result["metadata"]["saved"] is save
    assert SessionClient.entered == 0
    if save:
        relative = Path(result["metadata"]["resultPath"])
        assert not relative.is_absolute()
        path = tmp_path / relative
        assert path.name.startswith("sector_")
        assert json.loads(path.read_text(encoding="utf-8")) == result["builtin"]
    else:
        assert result["metadata"]["resultPath"] is None
        assert not (tmp_path / "results").exists()


def test_builtin_watchlist_sync_rejected_before_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    make_job(tmp_path, save=True, sync=True)
    monkeypatch.setattr(runner, "TradingViewClient", lambda: pytest.fail("No client"))
    result = asyncio.run(runner.run_job("sector", tmp_path))
    assert result["errors"][0]["code"] == "CONFIG_VALIDATION_ERROR"
    assert runner.job_exit_code(result) == 2


def test_unknown_builtin_does_not_open_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    make_job(tmp_path, save=False, definition="unknown")
    monkeypatch.setattr(runner, "TradingViewClient", lambda: pytest.fail("No client"))
    result = asyncio.run(runner.run_job("sector", tmp_path))
    assert result["errors"][0]["code"] == "JOB_TASK_UNAVAILABLE"



def test_jobs_list_accepts_known_builtin(tmp_path: Path) -> None:
    make_job(tmp_path, save=False)
    payload = runner.list_jobs(tmp_path)
    assert payload["status"] == "success"
    assert payload["jobs"][0]["task"] == {
        "type": "builtin", "definition": "us_sector_daily",
    }


def test_jobs_list_rejects_unknown_builtin(tmp_path: Path) -> None:
    make_job(tmp_path, save=False, definition="unknown")
    with pytest.raises(AppError) as caught:
        runner.list_jobs(tmp_path)
    assert caught.value.code == "JOB_TASK_UNAVAILABLE"


def test_jobs_list_rejects_builtin_watchlist_sync(tmp_path: Path) -> None:
    make_job(tmp_path, save=False, sync=True)
    with pytest.raises(ConfigError) as caught:
        runner.list_jobs(tmp_path)
    assert caught.value.code == "CONFIG_VALIDATION_ERROR"
    assert caught.value.field == "output.watchlistSync"


def test_provider_failure_does_not_save(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    make_job(tmp_path, save=True)
    class FailedClient(SessionClient):
        async def run_screener(self, request: Any) -> ObservedReadResponse:
            return response({"success": False, "error": "private provider text"}, text="private")
    monkeypatch.setattr(runner, "TradingViewClient", FailedClient)
    result = asyncio.run(runner.run_job("sector", tmp_path))
    assert result["status"] == "failed"
    assert result["errors"][0]["code"] == "PROVIDER_ERROR"
    assert "private" not in json.dumps(result)
    assert not (tmp_path / "results").exists()


def test_coverage_failure_does_not_save(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    make_job(tmp_path, save=True)
    class TruncatedClient(SessionClient):
        def __init__(self) -> None:
            super().__init__(total=2)
    monkeypatch.setattr(runner, "TradingViewClient", TruncatedClient)
    result = asyncio.run(runner.run_job("sector", tmp_path))
    assert result["errors"][0]["code"] == "US_SECTOR_COVERAGE_INCOMPLETE"
    assert result["builtin"] is None
    assert not (tmp_path / "results").exists()


def test_auth_failure_has_exit_three(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    make_job(tmp_path, save=True)
    class AuthClient(SessionClient):
        async def __aenter__(self) -> Self:
            raise AppError("AUTH_REQUIRED", "Authorization required")
    monkeypatch.setattr(runner, "TradingViewClient", AuthClient)
    result = asyncio.run(runner.run_job("sector", tmp_path))
    assert result["errors"][0]["code"] == "AUTH_REQUIRED"
    assert runner.job_exit_code(result) == 3


def test_result_write_failure_is_reported(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    make_job(tmp_path, save=True)
    monkeypatch.setattr(runner, "TradingViewClient", SessionClient)
    def fail_write(*_args: Any, **_kwargs: Any) -> Path:
        raise AppError("RESULT_WRITE_ERROR", "Cannot save result")
    monkeypatch.setattr(runner, "write_json_result", fail_write)
    result = asyncio.run(runner.run_job("sector", tmp_path))
    assert result["errors"][0]["code"] == "RESULT_WRITE_ERROR"
    assert result["metadata"]["saved"] is False


@pytest.mark.parametrize("code,expected_exit", [
    ("MCP_TOOL_UNAVAILABLE", 1),
    ("MCP_SCHEMA_MISMATCH", 1),
])
def test_client_failures_keep_error_code_and_skip_save(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, code: str, expected_exit: int,
) -> None:
    make_job(tmp_path, save=True)
    class FailedClient(SessionClient):
        async def get_screener_columns(self, request: Any) -> ObservedReadResponse:
            raise AppError(code, "Safe provider failure")
    monkeypatch.setattr(runner, "TradingViewClient", FailedClient)
    result = asyncio.run(runner.run_job("sector", tmp_path))
    assert result["errors"][0]["code"] == code
    assert runner.job_exit_code(result) == expected_exit
    assert not (tmp_path / "results").exists()


def test_builtin_job_uses_same_job_lock(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    make_job(tmp_path, save=False)
    monkeypatch.setattr(runner, "TradingViewClient", SessionClient)
    entered = asyncio.Event()
    release = asyncio.Event()

    async def delayed(client: Any) -> dict[str, Any]:
        entered.set()
        await release.wait()
        return await run_us_sector_daily(client)

    monkeypatch.setitem(runner.BUILTINS, "us_sector_daily", delayed)

    async def scenario() -> tuple[dict[str, Any], dict[str, Any]]:
        first = asyncio.create_task(runner.run_job("sector", tmp_path))
        await entered.wait()
        second = await runner.run_job("sector", tmp_path)
        release.set()
        return await first, second

    first, second = asyncio.run(scenario())
    assert first["status"] == "success"
    assert second["metadata"]["skipped"] is True
    assert second["metadata"]["reason"] == "already_running"


def test_writer_preserves_no_overwrite_and_finite_json(tmp_path: Path) -> None:
    from datetime import datetime

    instant = datetime.fromisoformat("2026-09-27T07:00:00+09:00")
    first = write_json_result({"a": 1}, name="sector", executed_at=instant, project_root=tmp_path)
    second = write_json_result({"a": 2}, name="sector", executed_at=instant, project_root=tmp_path)
    assert first != second
    assert first.read_text(encoding="utf-8") == '{"a":1}'
    with pytest.raises(AppError) as caught:
        write_json_result({"value": math.inf}, name="sector", executed_at=instant, project_root=tmp_path)
    assert caught.value.code == "RESULT_WRITE_ERROR"
    with pytest.raises(AppError):
        write_json_result({}, name="../unsafe", executed_at=instant, project_root=tmp_path)
