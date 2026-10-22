"""Offline export checks: no Provider credentials or network access required."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from tradingview_screening.export_results import export_file, main


def _result(rows: list[dict] | None = None, *, status: str = "success") -> dict:
    return {
        "schemaVersion": 1,
        "status": status,
        "operation": "screening",
        "name": "test_screen",
        "executedAt": "2026-10-22T15:00:00+09:00",
        "source": "tradingview_official_mcp",
        "metadata": {"returnedCount": 1, "totalCount": 10, "completeCoverage": False},
        "results": rows if rows is not None else [{
            "symbol": "TSE:5243", "name": "note", "close": 2738,
            "volume": 448700, "RSI|60": 30.72,
        }],
        "errors": [],
    }


def _write(tmp_path: Path, data: dict, name: str = "run.json") -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def test_html_export_creates_table_and_chart_link(tmp_path: Path) -> None:
    source = _write(tmp_path, _result())
    output = tmp_path / "run.html"
    assert export_file(source, output, "html", overwrite=False) == 1
    body = output.read_text(encoding="utf-8")
    assert "<!doctype html>" in body
    assert "TSE%3A5243" in body
    assert "30.72" in body
    assert "Provider total: 10" in body
    assert source.read_bytes() == json.dumps(_result(), ensure_ascii=False).encode("utf-8")


def test_csv_export_excel_encoding_and_column_union(tmp_path: Path) -> None:
    rows = [
        {"symbol": "TSE:A", "companyName": "=DANGER", "volume": 100},
        {"symbol": "TSE:B", "RSI|60": 32.1, "note": [1, 2]},
    ]
    source = _write(tmp_path, _result(rows))
    output = tmp_path / "run.csv"
    assert export_file(source, output, "csv", overwrite=False) == 2
    assert output.read_bytes().startswith(b"\xef\xbb\xbf")
    with output.open(encoding="utf-8-sig", newline="") as stream:
        csv_rows = list(csv.DictReader(stream))
    assert csv_rows[0]["companyName"] == "'=DANGER"
    assert csv_rows[1]["RSI|60"] == "32.1"
    assert csv_rows[1]["note"] == "[1, 2]"
    assert csv_rows[0]["RSI|60"] == ""


def test_html_escapes_untrusted_strings(tmp_path: Path) -> None:
    source = _write(tmp_path, _result([{
        "symbol": 'TSE:<script>alert(1)</script>', "description": '<img src=x onerror=alert(1)>',
    }]))
    output = tmp_path / "run.html"
    export_file(source, output, "html", overwrite=False)
    body = output.read_text(encoding="utf-8")
    assert "<script>" not in body
    assert "<img src=x" not in body
    assert "&lt;img src=x onerror=alert(1)&gt;" in body
    assert "TSE%3A%3Cscript%3E" in body


def test_custom_pipeline_result_uses_only_results_rows(tmp_path: Path) -> None:
    data = _result([{"symbol": "TSE:6574", "RSI|60": 32.7, "volumeRank": 87}])
    data["operation"] = "growth_volume_rsi"
    data["top100"] = [{"symbol": "TSE:OTHER", "RSI|60": 60}]
    data["metadata"] = {"universeCount": 594, "topCount": 100, "matchedCount": 1}
    source = _write(tmp_path, data)
    output = tmp_path / "run.csv"
    export_file(source, output, "csv", overwrite=False)
    assert "TSE:6574" in output.read_text(encoding="utf-8-sig")
    assert "TSE:OTHER" not in output.read_text(encoding="utf-8-sig")


def test_partial_result_is_labeled(tmp_path: Path) -> None:
    source = _write(tmp_path, _result(status="partial"))
    output = tmp_path / "run.html"
    export_file(source, output, "html", overwrite=False)
    assert "Partial result" in output.read_text(encoding="utf-8")


def test_failed_invalid_and_duplicate_keys_rejected(tmp_path: Path) -> None:
    source = _write(tmp_path, _result(status="failed"))
    with pytest.raises(ValueError, match="Only successful"):
        export_file(source, tmp_path / "run.csv", "csv", overwrite=False)
    source.write_text('{"status":"success","results":[],"results":[]}', encoding="utf-8")
    with pytest.raises(ValueError, match="Duplicate JSON key"):
        export_file(source, tmp_path / "run.csv", "csv", overwrite=False)
    source.write_text('{"status":"success","results":[1]}', encoding="utf-8")
    with pytest.raises(ValueError, match="array of objects"):
        export_file(source, tmp_path / "run.csv", "csv", overwrite=False)


def test_overwrite_is_explicit_and_source_is_preserved(tmp_path: Path) -> None:
    data = _result()
    source = _write(tmp_path, data)
    output = tmp_path / "run.csv"
    export_file(source, output, "csv", overwrite=False)
    with pytest.raises(FileExistsError, match="already exists"):
        export_file(source, output, "csv", overwrite=False)
    output.write_text("OLD", encoding="utf-8")
    export_file(source, output, "csv", overwrite=True)
    assert output.read_bytes() != b"OLD"
    with pytest.raises(ValueError, match="must not overwrite"):
        export_file(source, source, "html", overwrite=True)
    assert json.loads(source.read_text(encoding="utf-8")) == data


def test_cli_accepts_format_and_reports_missing_input(tmp_path: Path, capsys) -> None:
    source = _write(tmp_path, _result())
    assert main([str(source), "--format", "html"]) == 0
    assert source.with_suffix(".html").is_file()
    assert main([str(tmp_path / "missing.json"), "--format", "csv"]) == 1
    assert "does not exist" in capsys.readouterr().err
