from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from tradingview_screening import __main__ as cli
from tradingview_screening.common.errors import AppError, ConfigError
from tradingview_screening.screening.comparison import compare_results
from tradingview_screening.screening.fingerprint import definition_fingerprint
from tradingview_screening.screening.results import history_result, latest_result, save_result
from tradingview_screening.screening.schema import ScreeningDefinition


def _definition(**changes: object) -> ScreeningDefinition:
    data = {
        "schemaVersion": 1, "name": "sample", "market": "japan",
        "symbolTypes": ["stock"], "filters": {"close": [1, 10]},
        "limit": 2, "columns": ["close", "name"],
    }
    data.update(changes)
    return ScreeningDefinition.model_validate(data)


def _result(
    stamp: str, rows: list[dict] | None = None, *, total: int | None = None,
    fingerprint: dict | None = None,
) -> dict:
    rows = rows if rows is not None else [{"symbol": "TSE:A", "close": 1}]
    total = len(rows) if total is None else total
    metadata = {
        "requestedCount": 2, "requestedLimit": 2, "returnedCount": len(rows),
        "totalCount": total, "limitReached": len(rows) >= 2,
        "completeCoverage": len(rows) == total and len({row["symbol"] for row in rows}) == total,
        "partial": False, "durationMs": 1,
    }
    if fingerprint is not None:
        metadata["definitionFingerprint"] = fingerprint
    return {
        "schemaVersion": 1, "status": "success", "operation": "screening", "name": "sample",
        "executedAt": stamp, "source": "tradingview_official_mcp",
        "metadata": metadata, "results": rows, "errors": [],
    }


def test_fingerprint_canonical_selectors_and_defaults() -> None:
    base = _definition()
    reordered = _definition(filters={"close": [1, 10]})
    assert definition_fingerprint(base) == definition_fingerprint(reordered)
    assert definition_fingerprint(base) == definition_fingerprint(
        _definition(description="display", watchlist={"enabled": False}),
    )
    fingerprint = definition_fingerprint(base)
    assert fingerprint["version"] == 1
    assert fingerprint["algorithm"] == "sha256"
    assert len(fingerprint["value"]) == 64
    for changed in (
        {"market": "america"}, {"symbolTypes": ["fund"]}, {"filters": {"close": [2, 10]}},
        {"filterPreset": "oversold_healthy"}, {"symbolset": ["TSE:A"]},
        {"sortBy": "close"}, {"sortOrder": "asc"}, {"limit": 3},
        {"columns": ["name", "close"]},
    ):
        assert definition_fingerprint(_definition(**changed)) != fingerprint


def test_fingerprint_canonical_json_preserves_array_order() -> None:
    first = _definition(filters={"close": [1, 10], "market_cap_basic": [5, None]})
    second = _definition(filters={"market_cap_basic": [5, None], "close": [1, 10]})
    assert definition_fingerprint(first) == definition_fingerprint(second)
    selectors = first.model_dump(mode="json")
    canonical = json.dumps(
        {key: selectors[key] for key in (
            "market", "symbolTypes", "filters", "filterPreset", "symbolset",
            "sortBy", "sortOrder", "limit", "columns",
        )}, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False,
    ).encode("utf-8")
    assert definition_fingerprint(first)["value"] == hashlib.sha256(canonical).hexdigest()
    assert definition_fingerprint(_definition(columns=["name", "close"])) != definition_fingerprint(first)


def test_history_empty_multiple_days_serial_and_bad_files(tmp_path: Path) -> None:
    assert history_result(tmp_path, "sample")["items"] == []
    fp = definition_fingerprint(_definition())
    first = _result("2026-10-17T23:59:59+09:00", fingerprint=fp)
    second = _result("2026-10-18T00:00:00+09:00", fingerprint=fp)
    third = _result("2026-10-18T00:00:00+09:00", [{"symbol": "TSE:B"}], fingerprint=fp)
    save_result(first, tmp_path)
    same = save_result(second, tmp_path)
    later = save_result(third, tmp_path)
    (same.parent / "sample_235959.json").write_text("{broken", encoding="utf-8")
    items = history_result(tmp_path, "sample")["items"]
    assert [item["file"] for item in items] == [
        later.relative_to(tmp_path).as_posix(), same.relative_to(tmp_path).as_posix(),
        "results/2026-10-17/sample_235959.json",
    ]
    assert history_result(tmp_path, "sample", limit=2)["items"] == items[:2]
    assert items[0]["definitionFingerprint"] == fp
    assert items[0]["totalCount"] == 1
    assert items[0]["completeCoverage"] is True
    with pytest.raises(AppError, match="Invalid history limit"):
        history_result(tmp_path, "sample", limit=1001)


def test_compare_observed_changes_and_missing_null(tmp_path: Path) -> None:
    fp = definition_fingerprint(_definition())
    save_result(_result("2026-10-18T10:00:00+09:00", [
        {"symbol": "TSE:A", "close": 1, "name": None, "flag": True},
        {"symbol": "TSE:B", "close": 2},
    ], total=10, fingerprint=fp), tmp_path)
    save_result(_result("2026-10-18T11:00:00+09:00", [
        {"symbol": "TSE:A", "close": 1.0, "name": "A", "flag": 1, "new": None},
        {"symbol": "TSE:C", "close": 3},
    ], total=11, fingerprint=fp), tmp_path)
    compared = compare_results(tmp_path, "sample")
    assert compared["status"] == "success"
    assert compared["fingerprintMatched"] is True
    assert compared["comparisonScope"] == "observed_set_only"
    assert compared["observedAdded"] == ["TSE:C"]
    assert compared["observedRemoved"] == ["TSE:B"]
    assert compared["observedCommon"] == ["TSE:A"]
    assert compared["totalCountChange"] == 1
    fields = compared["indicatorChanges"][0]["fields"]
    assert "close" not in fields
    assert fields["flag"]["before"]["value"] is True
    assert fields["flag"]["after"]["value"] == 1
    assert fields["new"] == {"before": {"present": False}, "after": {"present": True, "value": None}}
    assert fields["name"]["before"] == {"present": True, "value": None}


def test_compare_row_order_alone_is_not_a_change(tmp_path: Path) -> None:
    fp = definition_fingerprint(_definition())
    first = [{"symbol": "TSE:B", "close": 2}, {"symbol": "TSE:A", "close": 1}]
    second = list(reversed(first))
    save_result(_result("2026-10-18T10:00:00+09:00", first, fingerprint=fp), tmp_path)
    save_result(_result("2026-10-18T11:00:00+09:00", second, fingerprint=fp), tmp_path)
    compared = compare_results(tmp_path, "sample")
    assert compared["status"] == "success"
    assert compared["observedAdded"] == []
    assert compared["observedRemoved"] == []
    assert compared["observedCommon"] == ["TSE:A", "TSE:B"]
    assert compared["indicatorChanges"] == []


def test_compare_full_coverage_and_legacy_unknown_count(tmp_path: Path) -> None:
    fp = definition_fingerprint(_definition())
    first = _result("2026-10-18T10:00:00+09:00", fingerprint=fp)
    second = _result("2026-10-18T11:00:00+09:00", fingerprint=fp)
    save_result(first, tmp_path)
    save_result(second, tmp_path)
    assert compare_results(tmp_path, "sample")["comparisonScope"] == "full_matched_set"
    for item in (first, second):
        for field in ("requestedLimit", "totalCount", "limitReached", "completeCoverage"):
            item["metadata"].pop(field)
    other = tmp_path / "legacy"
    save_result(first, other)
    save_result(second, other)
    assert compare_results(other, "sample")["totalCountChange"] is None
    assert compare_results(other, "sample")["comparisonScope"] == "observed_set_only"
    assert latest_result(other, "sample") == second


@pytest.mark.parametrize(("variant", "reason"), [
    ("missing", "MISSING_FINGERPRINT"),
    ("different_filter", "DEFINITION_MISMATCH"),
    ("different_limit", "DEFINITION_MISMATCH"),
    ("different_columns", "DEFINITION_MISMATCH"),
    ("unsupported", "UNSUPPORTED_FINGERPRINT"),
    ("invalid", "INVALID_FINGERPRINT"),
    ("null", "INVALID_FINGERPRINT"),
    ("duplicate_incomplete", "INVALID_SYMBOLS"),
    ("duplicate_complete", "INVALID_SYMBOLS"),
    ("bad_symbol", "INVALID_SYMBOLS"),
])
def test_compare_does_not_fall_back_from_newest_bad_pair(
    tmp_path: Path, variant: str, reason: str,
) -> None:
    fp = definition_fingerprint(_definition())
    save_result(_result("2026-10-18T09:00:00+09:00", fingerprint=fp), tmp_path)
    save_result(_result("2026-10-18T10:00:00+09:00", fingerprint=fp), tmp_path)
    newest = _result("2026-10-18T11:00:00+09:00", fingerprint=fp)
    if variant == "missing":
        newest["metadata"].pop("definitionFingerprint")
    elif variant.startswith("different_"):
        changed = {
            "different_filter": {"filters": {"close": [2, 10]}},
            "different_limit": {"limit": 3},
            "different_columns": {"columns": ["name", "close"]},
        }[variant]
        newest["metadata"]["definitionFingerprint"] = definition_fingerprint(_definition(**changed))
    elif variant == "unsupported":
        newest["metadata"]["definitionFingerprint"] = {**fp, "version": 2}
    elif variant == "invalid":
        newest["metadata"]["definitionFingerprint"] = []
    elif variant == "null":
        newest["metadata"]["definitionFingerprint"] = None
    elif variant.startswith("duplicate_"):
        newest["results"] = [{"symbol": "TSE:A"}, {"symbol": "TSE:A"}]
        newest["metadata"].update({
            "returnedCount": 2, "totalCount": 2, "limitReached": True,
            "completeCoverage": variant == "duplicate_complete",
        })
    else:
        newest["results"] = [{"symbol": "TSE:A:B"}]
    folder = tmp_path / "results" / "2026-10-18"
    (folder / "sample_110000.json").write_text(json.dumps(newest), encoding="utf-8")
    compared = compare_results(tmp_path, "sample")
    assert compared["status"] == "not_comparable"
    assert compared["reason"] == reason
    if variant.startswith("different_"):
        assert compared["fingerprintMatched"] is False
    assert compared["to"]["executedAt"] == newest["executedAt"]
    if variant in {"invalid", "null"}:
        assert compared["to"]["definitionFingerprint"] is None


def test_compare_accepts_existing_symbol_shape_and_rejects_bad_values(tmp_path: Path) -> None:
    fp = definition_fingerprint(_definition())
    save_result(_result("2026-10-18T10:00:00+09:00", [
        {"symbol": "TSE!:A!", "close": 1},
    ], fingerprint=fp), tmp_path)
    save_result(_result("2026-10-18T11:00:00+09:00", [
        {"symbol": "TSE!:A!", "close": 2},
    ], fingerprint=fp), tmp_path)
    assert compare_results(tmp_path, "sample")["observedCommon"] == ["TSE!:A!"]
    malformed = _result("2026-10-18T12:00:00+09:00", [
        {"symbol": "TSE!:A!", "close": {"nested": True}},
    ], fingerprint=fp)
    folder = tmp_path / "results" / "2026-10-18"
    (folder / "sample_120000.json").write_text(json.dumps(malformed), encoding="utf-8")
    assert compare_results(tmp_path, "sample")["reason"] == "INVALID_VALUES"


def test_history_excludes_duplicate_json_keys_and_inconsistent_metadata(tmp_path: Path) -> None:
    fp = definition_fingerprint(_definition())
    valid = _result("2026-10-18T10:00:00+09:00", fingerprint=fp)
    save_result(valid, tmp_path)
    folder = tmp_path / "results" / "2026-10-18"
    duplicated_key = json.dumps(_result("2026-10-18T11:00:00+09:00", fingerprint=fp))
    duplicated_key = duplicated_key.replace('"status": "success"', '"status": "success", "status": "success"')
    (folder / "sample_110000.json").write_text(duplicated_key, encoding="utf-8")
    inconsistent = _result("2026-10-18T12:00:00+09:00", fingerprint=fp)
    inconsistent["metadata"]["completeCoverage"] = False
    (folder / "sample_120000.json").write_text(json.dumps(inconsistent), encoding="utf-8")
    assert len(history_result(tmp_path, "sample")["items"]) == 1
    assert compare_results(tmp_path, "sample")["reason"] == "INVALID_METADATA"


def test_history_skips_nonfinite_json(tmp_path: Path) -> None:
    fp = definition_fingerprint(_definition())
    valid = _result("2026-10-18T10:00:00+09:00", fingerprint=fp)
    path = save_result(valid, tmp_path)
    folder = path.parent
    nonfinite = json.dumps(_result("2026-10-18T11:00:00+09:00", fingerprint=fp))
    (folder / "sample_110000.json").write_text(
        nonfinite.replace('"close": 1', '"close": 1e999'), encoding="utf-8",
    )
    assert [item["file"] for item in history_result(tmp_path, "sample")["items"]] == [
        path.relative_to(tmp_path).as_posix(),
    ]


def test_history_compare_reject_traversal_name(tmp_path: Path) -> None:
    for operation in (history_result, compare_results):
        with pytest.raises(ConfigError) as caught:
            operation(tmp_path, "../secret")
        assert caught.value.code == "CONFIG_NAME_INVALID"


def test_history_compare_reject_results_root_escape(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    results_root = tmp_path / "results"
    outside = tmp_path.parent / "outside-results"
    original_resolve = Path.resolve

    def escaping_root(path: Path, *args: object, **kwargs: object) -> Path:
        return outside if path == results_root else original_resolve(path, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", escaping_root)
    for operation in (history_result, compare_results):
        with pytest.raises(AppError) as caught:
            operation(tmp_path, "sample")
        assert caught.value.code == "RESULT_READ_ERROR"


def test_history_compare_ignore_symlink_file(tmp_path: Path) -> None:
    fp = definition_fingerprint(_definition())
    path = save_result(_result("2026-10-18T10:00:00+09:00", fingerprint=fp), tmp_path)
    link = path.parent / "sample_100000_1.json"
    try:
        link.symlink_to(path)
    except OSError as exc:
        pytest.skip(f"Symlink creation unavailable: {type(exc).__name__}")
    assert link.is_symlink()
    assert len(history_result(tmp_path, "sample")["items"]) == 1
    assert compare_results(tmp_path, "sample")["reason"] == "NO_BASELINE"


def test_compare_one_snapshot_reports_no_baseline(tmp_path: Path) -> None:
    fp = definition_fingerprint(_definition())
    save_result(_result("2026-10-18T10:00:00+09:00", fingerprint=fp), tmp_path)
    compared = compare_results(tmp_path, "sample")
    assert compared["status"] == "not_comparable"
    assert compared["reason"] == "NO_BASELINE"
    assert compared["from"] is None
    assert compared["to"]["executedAt"] == "2026-10-18T10:00:00+09:00"


def test_compare_no_baseline_and_cli_read_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("remote or write path called")
    monkeypatch.setattr(cli, "TradingViewClient", forbidden)
    monkeypatch.setattr(cli, "run_job", forbidden)
    monkeypatch.setattr(cli, "save_result", forbidden)
    monkeypatch.setattr(cli, "create_token_storage", forbidden)
    assert cli.main(["results", "history", "sample"]) == 0
    assert json.loads(capsys.readouterr().out)["items"] == []
    assert cli.main(["results", "compare", "sample"]) == 1
    assert json.loads(capsys.readouterr().out)["reason"] == "NO_BASELINE"
    assert not (tmp_path / "results").exists()


def test_cli_history_compare_and_invalid_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    fp = definition_fingerprint(_definition())
    first = save_result(_result("2026-10-18T10:00:00+09:00", fingerprint=fp), tmp_path)
    second = save_result(_result("2026-10-18T11:00:00+09:00", fingerprint=fp), tmp_path)
    saved = {path: path.read_bytes() for path in (first, second)}
    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("remote or write path called")
    for name in (
        "TradingViewClient", "create_token_storage", "run_job", "save_result",
        "apply_schedules", "list_schedules", "remove_schedule", "_execute_screen", "_execute",
        "_credential_present",
    ):
        monkeypatch.setattr(cli, name, forbidden)
    monkeypatch.setattr(
        "tradingview_screening.screening.watchlist_sync.sync_screening_watchlist", forbidden,
    )
    monkeypatch.chdir(tmp_path)
    assert cli.main(["results", "history", "sample", "--limit", "1"]) == 0
    assert len(json.loads(capsys.readouterr().out)["items"]) == 1
    assert cli.main(["results", "compare", "sample"]) == 0
    assert json.loads(capsys.readouterr().out)["comparisonScope"] == "full_matched_set"
    for value in ("0", "1001"):
        assert cli.main(["results", "history", "sample", "--limit", value]) == 2
        captured = capsys.readouterr()
        assert json.loads(captured.out)["error"]["code"] == "CLI_USAGE_ERROR"
    assert {path: path.read_bytes() for path in saved} == saved


@pytest.mark.parametrize(("command", "target"), [
    (["results", "latest", "sample"], "latest_result"),
    (["results", "history", "sample"], "history_result"),
    (["results", "compare", "sample"], "compare_results"),
])
def test_cli_results_unexpected_read_exception_is_local_error(
    command: list[str], target: str, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("private local value")
    monkeypatch.setattr(cli, target, fail)
    assert cli.main(command) == 1
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["error"]["code"] == "RESULT_READ_ERROR"
    assert payload["operation"] == f"results_{command[1]}"
    assert "private local value" not in captured.out + captured.err
