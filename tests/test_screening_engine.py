from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Self

import pytest

from tradingview_screening import __main__ as cli
from tradingview_screening.common.errors import AppError, ConfigError
from tradingview_screening.integrations.tradingview.client import (
    ToolCatalog,
    ToolInfo,
    TradingViewClient,
)
from tradingview_screening.integrations.tradingview.schemas import (
    ObservedReadResponse,
    RunScreenerRequest,
)
from tradingview_screening.integrations.tradingview.screener_normalization import normalize_screener
from tradingview_screening.screening.engine import run_screening, to_screener_request
from tradingview_screening.screening.results import latest_result, save_result
from tradingview_screening.screening.validators import load_screening_by_name, validate_screening


def definition(name: str = "sample") -> dict:
    return {
        "schemaVersion": 1,
        "name": name,
        "market": "japan",
        "symbolTypes": ["stock"],
        "filters": {"price_earnings_ttm": [None, 15]},
        "sortBy": "change",
        "sortOrder": "desc",
        "limit": 1,
        "columns": ["name", "close"],
        "watchlist": {"enabled": True, "name": "ignored in phase 6"},
    }


def write_definition(root: Path, name: str = "sample") -> None:
    directory = root / "screenings"
    directory.mkdir()
    (directory / f"{name}.json").write_text(json.dumps(definition(name)), encoding="utf-8")


def response(payload: dict | None) -> ObservedReadResponse:
    return ObservedReadResponse.model_validate({"structured_content": payload, "content": []})


def success(rows: list[dict] | None = None) -> ObservedReadResponse:
    return response({"success": True, "data": {"rows": rows or [], "totalCount": len(rows or [])}})


class FakeClient:
    received: RunScreenerRequest | None = None
    reply: ObservedReadResponse = success()
    failure: AppError | None = None

    async def __aenter__(self) -> Self:
        if self.failure is not None:
            raise self.failure
        return self

    async def __aexit__(self, *_args: object) -> None:
        pass

    async def run_screener(self, request: RunScreenerRequest) -> ObservedReadResponse:
        self.received = request
        if self.failure is not None:
            raise self.failure
        return self.reply


def test_loader_and_safe_name(tmp_path: Path) -> None:
    write_definition(tmp_path)
    assert load_screening_by_name("sample", tmp_path).name == "sample"
    with pytest.raises(ConfigError) as missing:
        load_screening_by_name("missing", tmp_path)
    assert missing.value.code == "CONFIG_FILE_NOT_FOUND"
    with pytest.raises(ConfigError) as traversal:
        load_screening_by_name("../secret", tmp_path)
    assert traversal.value.code == "CONFIG_NAME_INVALID"


def test_mapping_preserves_filters_and_ignores_watchlist() -> None:
    request = to_screener_request(validate_screening(definition()))
    assert request.model_dump(mode="json", exclude_unset=True) == {
        "market": "japan", "filters": {"price_earnings_ttm": [None, 15]},
        "sort_by": "change", "sort_order": "desc", "limit": 1,
        "columns": ["name", "close"], "symbol_types": ["stock"],
    }


def test_mapping_omits_optional_sort_without_sending_null() -> None:
    data = definition()
    del data["sortBy"]
    request = to_screener_request(validate_screening(data))
    assert "sort_by" not in request.model_dump(mode="json", exclude_unset=True)


def test_typed_client_path_and_success_normalization() -> None:
    client = FakeClient()
    client.reply = success([{
        "symbol": "TSE:7203", "name": "Toyota", "close": 100,
        "provider_extra": "discard",
    }])
    result = asyncio.run(run_screening(validate_screening(definition()), client))
    assert isinstance(client.received, RunScreenerRequest)
    assert result["results"] == [{"symbol": "TSE:7203", "name": "Toyota", "close": 100}]
    assert result["metadata"]["requestedCount"] == 1
    assert result["metadata"]["returnedCount"] == 1
    assert result["metadata"]["partial"] is False
    assert "cacheHit" not in result["metadata"]
    assert result["executedAt"].endswith("+09:00")
    assert result["errors"] == []


def test_real_typed_wrapper_sdk_governor_and_content_ignored() -> None:
    class Sdk:
        def __init__(self) -> None:
            self.calls: list[tuple[str, dict]] = []

        async def call_tool(self, name: str, arguments: dict) -> SimpleNamespace:
            self.calls.append((name, arguments))
            return SimpleNamespace(
                is_error=False,
                structured_content={"success": True, "data": {
                    "rows": [{"symbol": "TSE:7203", "name": "Toyota", "close": 100}],
                    "totalCount": 1,
                }},
                content=[SimpleNamespace(model_dump=lambda **_kwargs: {
                    "type": "text", "text": "secret provider raw content",
                })],
            )

    sdk = Sdk()
    client = TradingViewClient()
    client._sdk = sdk
    client._catalog = ToolCatalog(
        (ToolInfo("mcp-tv-run-screener", None, None, {}, True, True),), (), (),
    )
    payload = asyncio.run(run_screening(validate_screening(definition()), client))
    assert sdk.calls[0][0] == "mcp-tv-run-screener"
    assert sdk.calls[0][1]["filters"] == {"price_earnings_ttm": [None, 15]}
    assert payload["results"] == [{"symbol": "TSE:7203", "name": "Toyota", "close": 100}]
    assert "secret" not in json.dumps(payload)


def test_more_rows_than_requested_is_schema_mismatch() -> None:
    client = FakeClient()
    client.reply = success([
        {"symbol": "TSE:7203", "name": "Toyota", "close": 100},
        {"symbol": "TSE:6758", "name": "Sony", "close": 200},
    ])
    with pytest.raises(AppError) as caught:
        asyncio.run(run_screening(validate_screening(definition()), client))
    assert caught.value.code == "MCP_SCHEMA_MISMATCH"


@pytest.mark.parametrize("payload", [
    None,
    {"success": True},
    {"success": True, "data": {"rows": {}, "totalCount": 1}},
    {"success": True, "data": {"rows": [], "totalCount": "0"}},
    {"success": True, "data": {"rows": [{"symbol": "TSE:7203", "name": "x"}], "totalCount": 1}},
    {"success": True, "data": {"rows": [{"name": "x", "close": 1}], "totalCount": 1}},
])
def test_malformed_structured_content_is_schema_mismatch(payload: dict | None) -> None:
    with pytest.raises(AppError) as caught:
        normalize_screener(response(payload), ["name", "close"])
    assert caught.value.code == "MCP_SCHEMA_MISMATCH"


@pytest.mark.parametrize(("error", "code"), [
    ("provider internal 429 with secret token", "PROVIDER_RATE_LIMITED"),
    ("unrelated provider failure with secret token", "PROVIDER_ERROR"),
])
def test_provider_business_failure_is_sanitized(error: str, code: str) -> None:
    with pytest.raises(AppError) as caught:
        normalize_screener(response({"success": False, "error": error}), ["name"])
    assert caught.value.code == code
    assert "secret" not in str(caught.value)


def result(name: str, stamp: str, symbol: str = "TSE:7203") -> dict:
    return {
        "schemaVersion": 1, "status": "success", "operation": "screening", "name": name,
        "executedAt": stamp, "source": "tradingview_official_mcp",
        "metadata": {"requestedCount": 1, "returnedCount": 1, "partial": False, "durationMs": 12},
        "results": [{"symbol": symbol, "name": "Toyota"}], "errors": [],
    }


def test_result_write_date_filename_collision_atomic_and_no_raw(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    payload = result("sample", "2026-09-26T00:01:02+09:00")
    calls: list[tuple[Path, Path]] = []
    from tradingview_screening.screening import results as module
    original_link = module.os.link

    def observed_link(source: Path, destination: Path) -> None:
        assert source.exists()
        assert destination.suffix == ".json"
        assert json.loads(source.read_text(encoding="utf-8"))["schemaVersion"] == 1
        calls.append((source, destination))
        original_link(source, destination)

    monkeypatch.setattr(module.os, "link", observed_link)
    first = save_result(payload, tmp_path)
    different = result("sample", "2026-09-26T00:01:02+09:00", symbol="TSE:6758")
    second = save_result(different, tmp_path)
    assert first.name == "sample_000102.json"
    assert second.name == "sample_000102_1.json"
    assert first.parent.name == "2026-09-26"
    assert json.loads(first.read_text(encoding="utf-8")) == payload
    assert json.loads(second.read_text(encoding="utf-8")) == different
    assert calls and not list(first.parent.glob("*.tmp"))
    assert json.loads(first.read_text(encoding="utf-8")) == payload
    assert "structured_content" not in first.read_text(encoding="utf-8")


def test_result_publish_failure_cleans_temporary_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from tradingview_screening.screening import results as module

    def fail_link(_source: Path, _destination: Path) -> None:
        raise OSError("publish failed")

    monkeypatch.setattr(module.os, "link", fail_link)
    with pytest.raises(AppError) as caught:
        save_result(result("sample", "2026-09-26T00:01:02+09:00"), tmp_path)
    assert caught.value.code == "RESULT_WRITE_ERROR"
    assert list((tmp_path / "results").rglob("*.*")) == []


def test_result_fsync_failure_cleans_temporary_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tradingview_screening.screening import results as module

    def fail_fsync(_descriptor: int) -> None:
        raise OSError("flush failed")

    monkeypatch.setattr(module.os, "fsync", fail_fsync)
    with pytest.raises(AppError) as caught:
        save_result(result("sample", "2026-09-26T00:01:02+09:00"), tmp_path)
    assert caught.value.code == "RESULT_WRITE_ERROR"
    assert list((tmp_path / "results").rglob("*.*")) == []


def test_cleanup_failure_does_not_hide_published_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tradingview_screening.screening import results as module
    original_unlink = module.Path.unlink

    def fail_temporary_unlink(path: Path, *args: object, **kwargs: object) -> None:
        if path.suffix == ".tmp":
            raise OSError("cleanup failed")
        original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(module.Path, "unlink", fail_temporary_unlink)
    payload = result("sample", "2026-09-26T00:01:02+09:00")
    published = save_result(payload, tmp_path)
    assert json.loads(published.read_text(encoding="utf-8")) == payload


def test_utc_time_is_saved_in_tokyo_next_day(tmp_path: Path) -> None:
    path = save_result(result("sample", "2026-09-25T16:01:02+00:00"), tmp_path)
    assert path.parent.name == "2026-09-26"
    assert path.name == "sample_010102.json"
    assert latest_result(tmp_path) == json.loads(path.read_text(encoding="utf-8"))


def test_latest_across_days_and_by_name(tmp_path: Path) -> None:
    earlier = result("sample", "2026-09-25T23:59:59+09:00")
    later = result("other", "2026-09-26T00:00:01+09:00")
    save_result(earlier, tmp_path)
    save_result(later, tmp_path)
    assert latest_result(tmp_path) == later
    assert latest_result(tmp_path, "sample") == earlier


def test_latest_skips_irrelevant_and_corrupt_json(tmp_path: Path) -> None:
    valid = result("sample", "2026-09-26T12:00:00+09:00")
    folder = save_result(valid, tmp_path).parent
    (folder / "other_235959.json").write_text("{broken", encoding="utf-8")
    (folder / "sample_235959.json").write_text('{"unexpected":true}', encoding="utf-8")
    (folder / "sample_235958.json").write_text("NaN", encoding="utf-8")
    infinite = result("sample", "2026-09-26T23:59:57+09:00")
    (folder / "sample_235957.json").write_text(
        json.dumps(infinite).replace('"name": "Toyota"', '"name": "Toyota", "close": 1e999'),
        encoding="utf-8",
    )
    assert latest_result(tmp_path) == valid
    with pytest.raises(ConfigError):
        latest_result(tmp_path, "../escape")
    with pytest.raises(AppError) as missing:
        latest_result(tmp_path, "other")
    assert missing.value.code == "RESULT_NOT_FOUND"


def test_results_root_resolving_outside_project_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "results"
    outside = tmp_path.parent / "outside-results"
    original_resolve = Path.resolve

    def external_root(path: Path, *args: object, **kwargs: object) -> Path:
        return outside if path == root else original_resolve(path, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", external_root)
    with pytest.raises(AppError) as write_error:
        save_result(result("sample", "2026-09-26T12:00:00+09:00"), tmp_path)
    assert write_error.value.code == "RESULT_WRITE_ERROR"
    with pytest.raises(AppError) as read_error:
        latest_result(tmp_path)
    assert read_error.value.code == "RESULT_READ_ERROR"


def test_result_day_resolving_outside_results_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "results"
    day = root / "2026-09-26"
    day.mkdir(parents=True)
    outside = tmp_path.parent / "outside-day"
    original_resolve = Path.resolve

    def external_day(path: Path, *args: object, **kwargs: object) -> Path:
        return outside if path == day else original_resolve(path, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", external_day)
    with pytest.raises(AppError) as write_error:
        save_result(result("sample", "2026-09-26T12:00:00+09:00"), tmp_path)
    assert write_error.value.code == "RESULT_WRITE_ERROR"
    with pytest.raises(AppError) as read_error:
        latest_result(tmp_path)
    assert read_error.value.code == "RESULT_NOT_FOUND"


def test_latest_rejects_filename_name_and_date_mismatches(tmp_path: Path) -> None:
    root = tmp_path / "results"
    correct_day = root / "2026-09-26"
    wrong_day = root / "2026-09-27"
    correct_day.mkdir(parents=True)
    wrong_day.mkdir(parents=True)
    payload = result("sample", "2026-09-26T12:00:00+09:00")
    body = json.dumps(payload)
    (correct_day / "sample_120001.json").write_text(body, encoding="utf-8")
    (correct_day / "other_120000.json").write_text(body, encoding="utf-8")
    (wrong_day / "sample_120000.json").write_text(body, encoding="utf-8")
    with pytest.raises(AppError) as caught:
        latest_result(tmp_path)
    assert caught.value.code == "RESULT_NOT_FOUND"


def test_partial_requires_usable_rows(tmp_path: Path) -> None:
    empty_partial = result("sample", "2026-09-26T12:00:00+09:00")
    empty_partial["status"] = "partial"
    empty_partial["metadata"]["partial"] = True
    empty_partial["metadata"]["returnedCount"] = 0
    empty_partial["results"] = []
    empty_partial["errors"] = [{"code": "PROVIDER_ERROR", "message": "Partial failure"}]
    with pytest.raises(AppError) as write_error:
        save_result(empty_partial, tmp_path)
    assert write_error.value.code == "RESULT_WRITE_ERROR"
    folder = tmp_path / "results" / "2026-09-26"
    folder.mkdir(parents=True)
    (folder / "sample_120000.json").write_text(json.dumps(empty_partial), encoding="utf-8")
    with pytest.raises(AppError) as read_error:
        latest_result(tmp_path)
    assert read_error.value.code == "RESULT_NOT_FOUND"


@pytest.mark.parametrize("mutation", [
    {"status": []},
    {"results": [123], "metadata": {"requestedCount": 1, "returnedCount": 1, "partial": False, "durationMs": 12}},
    {"errors": [{"unrelated": "value"}]},
    {"metadata": {"requestedCount": 1, "returnedCount": 999, "partial": False, "durationMs": 12}},
    {"executedAt": "0001-01-01T00:00:00+14:00"},
])
def test_latest_skips_json_valid_malformed_results(tmp_path: Path, mutation: dict) -> None:
    valid = result("sample", "2026-09-26T12:00:00+09:00")
    folder = save_result(valid, tmp_path).parent
    invalid = valid | mutation
    (folder / "sample_235959.json").write_text(json.dumps(invalid), encoding="utf-8")
    assert latest_result(tmp_path) == valid


def test_latest_timezone_absolute_order_and_deterministic_tie(tmp_path: Path) -> None:
    first = result("a", "2026-09-26T12:00:00+09:00")
    same = result("b", "2026-09-26T03:00:00+00:00")
    later = result("c", "2026-09-26T03:00:01+00:00")
    save_result(first, tmp_path)
    save_result(same, tmp_path)
    assert latest_result(tmp_path) == same
    save_result(later, tmp_path)
    assert latest_result(tmp_path) == later


def test_cli_screen_stdout_persistence_and_exit_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    write_definition(tmp_path)
    FakeClient.reply = success([{"symbol": "TSE:7203", "name": "Toyota", "close": 100}])
    FakeClient.failure = None
    monkeypatch.setattr(cli, "TradingViewClient", FakeClient)
    payload = asyncio.run(cli._execute_screen(
        load_screening_by_name("sample", tmp_path), tmp_path, started=cli.time.monotonic(),
    ))
    assert latest_result(tmp_path) == payload

    async def fake_execute(_screening: object, _root: Path, *, started: float) -> dict:
        return payload

    monkeypatch.setattr(cli, "_execute_screen", fake_execute)
    monkeypatch.chdir(tmp_path)
    assert cli.main(["screen", "sample"]) == 0
    captured = capsys.readouterr()
    assert len(captured.out.splitlines()) == 1
    assert json.loads(captured.out) == payload
    assert captured.err == ""


@pytest.mark.parametrize(("command", "error", "expected"), [
    (["screen", "sample"], AppError("PROVIDER_ERROR", "TradingView screener request failed"), 1),
    (["screen", "sample"], ConfigError("CONFIG_NAME_INVALID", "Invalid configuration name"), 2),
    (["screen", "sample"], AppError("AUTH_REQUIRED", "TradingView authorization is required"), 3),
])
def test_cli_screen_failure_exit_codes_and_envelope(
    command: list[str], error: Exception, expected: int,
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    write_definition(tmp_path)
    monkeypatch.chdir(tmp_path)

    async def fail(_screening: object, _root: Path, *, started: float) -> dict:
        raise error

    monkeypatch.setattr(cli, "_execute_screen", fail)
    assert cli.main(command) == expected
    captured = capsys.readouterr()
    assert len(captured.out.splitlines()) == 1
    payload = json.loads(captured.out)
    assert set(payload) == {
        "schemaVersion", "status", "operation", "name", "executedAt", "source",
        "metadata", "results", "errors",
    }
    assert payload["status"] == "failed"
    assert payload["errors"][0]["code"] == error.code
    assert payload["metadata"]["requestedCount"] == 1
    assert payload["metadata"]["durationMs"] >= 0
    assert not (tmp_path / "results").exists()


def test_cli_real_failure_does_not_save_and_usage_is_two(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    write_definition(tmp_path)
    monkeypatch.chdir(tmp_path)
    FakeClient.failure = AppError("AUTH_REQUIRED", "TradingView authorization is required")
    monkeypatch.setattr(cli, "TradingViewClient", FakeClient)
    assert cli.main(["screen", "sample"]) == 3
    payload = json.loads(capsys.readouterr().out)
    assert payload["metadata"]["requestedCount"] == 1
    assert not (tmp_path / "results").exists()
    assert cli.main(["screen"]) == 2
    assert json.loads(capsys.readouterr().out)["error"]["code"] == "CLI_USAGE_ERROR"
    FakeClient.failure = None


def test_cli_results_latest_routes_and_absence(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    observed: list[str | None] = []
    payload = result("sample", "2026-09-26T12:00:00+09:00")

    def fake_latest(_root: Path, name: str | None = None) -> dict:
        observed.append(name)
        return payload

    monkeypatch.setattr(cli, "latest_result", fake_latest)
    assert cli.main(["results", "latest"]) == 0
    assert json.loads(capsys.readouterr().out) == payload
    assert cli.main(["results", "latest", "sample"]) == 0
    assert json.loads(capsys.readouterr().out) == payload
    assert observed == [None, "sample"]

    def missing(_root: Path, _name: str | None = None) -> dict:
        raise AppError("RESULT_NOT_FOUND", "No screening result found")

    monkeypatch.setattr(cli, "latest_result", missing)
    assert cli.main(["results", "latest"]) == 1
    assert json.loads(capsys.readouterr().out)["error"]["code"] == "RESULT_NOT_FOUND"
