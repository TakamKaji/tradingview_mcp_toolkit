"""Offline export checks: no Provider credentials or network access required."""

from __future__ import annotations

import csv
import io
import json
from html.parser import HTMLParser
from pathlib import Path

import pytest

from tradingview_screening.export_results import export_file, main, render_csv, render_html


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
    assert 'data-en="Provider total"' in body
    assert "Provider総数" in body
    assert '<html lang="ja">' in body
    assert '<option value="ja" selected>' in body
    assert "document.documentElement.lang = lang" in body
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
    assert csv_rows[0]["会社名"] == "'=DANGER"
    assert csv_rows[1]["RSI（1時間足）"] == "32.1"
    assert csv_rows[1]["note"] == "[1, 2]"
    assert csv_rows[0]["RSI（1時間足）"] == ""


def test_html_escapes_untrusted_strings(tmp_path: Path) -> None:
    source = _write(tmp_path, _result([{
        "symbol": 'TSE:<script>alert(1)</script>', "description": '<img src=x onerror=alert(1)>',
    }]))
    output = tmp_path / "run.html"
    export_file(source, output, "html", overwrite=False)
    body = output.read_text(encoding="utf-8")
    assert body.count("<script>") == 1  # Only the fixed language-switch script.
    assert "<script>alert(1)</script>" not in body
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
    body = output.read_text(encoding="utf-8")
    assert "一部のデータを取得できませんでした" in body
    assert 'data-en="Partial result:' in body


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


def test_csv_bilingual_columns_and_unknown_keys() -> None:
    row = {
        "symbol": "TSE:1", "companyName": "A", "name": "A", "description": "B",
        "close": 1, "change": -1.5, "volume": 2, "volumeRank": 3,
        "RSI": 40, "RSI|60": 42, "customMetric": 7,
    }
    expected = {
        "ja": ["銘柄コード", "会社名", "表示名", "銘柄概要", "出来高順位", "終値",
               "騰落率（%）", "出来高", "RSI", "RSI（1時間足）", "customMetric"],
        "en": ["Symbol", "Company", "Name", "Description", "Volume rank", "Close",
               "Change (%)", "Volume", "RSI", "RSI (1h)", "customMetric"],
    }
    payload = _result([row])
    original = json.dumps(payload, ensure_ascii=False)
    for lang in ("ja", "en"):
        stream = io.StringIO()
        render_csv(payload, stream, lang)
        reader = csv.reader(io.StringIO(stream.getvalue()))
        assert next(reader) == expected[lang]
        assert next(reader)[6] == "-1.5"
    assert json.dumps(payload, ensure_ascii=False) == original


def test_csv_collision_and_formula_values_keep_columns_distinct() -> None:
    payload = _result([{
        "symbol": "=HYPERLINK()", "Symbol": "unknown", "Symbol [symbol]": "another",
        "close": -4, "change": "-4", "volume": "+SUM(1)",
        "description": "\t@DANGER", "note": " @DANGER",
        "=HEADER": "custom",
        "'=HEADER": "quoted custom",
    }])
    stream = io.StringIO()
    render_csv(payload, stream, "en")
    reader = csv.DictReader(io.StringIO(stream.getvalue()))
    assert len(reader.fieldnames) == len(set(reader.fieldnames))
    assert "Symbol" in reader.fieldnames
    assert "Symbol [symbol]" in reader.fieldnames
    assert "Symbol [symbol] (2)" in reader.fieldnames
    row = next(reader)
    assert row["Symbol [symbol] (2)"] == "'=HYPERLINK()"
    assert row["Symbol"] == "unknown"
    assert row["Symbol [symbol]"] == "another"
    assert row["Close"] == "-4"
    assert row["Change (%)"] == "'-4"
    assert row["Volume"] == "'+SUM(1)"
    assert row["Description"] == "'\t@DANGER"
    assert row["note"] == "' @DANGER"
    assert row["'=HEADER [=HEADER]"] == "custom"
    assert row["'=HEADER"] == "quoted custom"


def test_html_language_content_and_untrusted_values() -> None:
    payload = _result([{"symbol": 'TSE:</script><img src=x>', "description": '" onmouseover="bad'}])
    payload["name"] = '</script><img src=x onerror="bad">'
    payload["metadata"] = {"totalCount": 8, "completeCoverage": True, "topCount": 4}
    for lang in ("ja", "en"):
        body = render_html(payload, lang)
        assert f'<html lang="{lang}">' in body
        assert f'<option value="{lang}" selected>' in body
        assert "&lt;/script&gt;&lt;img src=x" in body
        assert "TSE%3A%3C%2Fscript%3E" in body
        assert 'data-ja="銘柄コード" data-en="Symbol"' in body
        assert 'data-ja="全件取得" data-en="Complete coverage"' in body
        assert 'data-ja="はい" data-en="Yes"' in body
        assert 'data-ja="成功" data-en="Success"' in body
        assert 'data-ja="保存済みJSONからローカルで生成しました。' in body
        assert "node.textContent = node.getAttribute('data-' + lang)" in body
        assert body.count("<script>") == 1
        assert '<img src=x onerror="bad">' not in body
    assert render_html(payload, "en") != render_html(payload, "ja")


def test_empty_partial_and_missing_metadata_have_bilingual_html() -> None:
    payload = _result([], status="partial")
    payload.pop("metadata")
    payload.pop("name")
    body = render_html(payload)
    assert "結果はありません。" in body
    assert 'data-en="No results."' in body
    assert 'data-en="Partial result:' in body
    assert 'data-en="Partial"' in body
    assert 'colspan="1"' in body
    assert "スクリーニング結果" in body
    assert "Provider総数" not in body
    stream = io.StringIO()
    render_csv(payload, stream)
    assert stream.getvalue() == "銘柄コード\r\n"


def test_html_initial_language_matches_visible_localized_text() -> None:
    class LocalizedElements(HTMLParser):
        def __init__(self) -> None:
            super().__init__(convert_charrefs=True)
            self.language: str | None = None
            self.selected: list[str] = []
            self.elements: list[tuple[str, str, str]] = []
            self.current: tuple[str, str, str, list[str]] | None = None

        def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            attributes = dict(attrs)
            if tag == "html":
                self.language = attributes["lang"]
            if tag == "option" and "selected" in attributes:
                self.selected.append(attributes["value"])
            if "data-ja" in attributes and "data-en" in attributes:
                assert self.current is None
                self.current = (tag, attributes["data-ja"], attributes["data-en"], [])

        def handle_data(self, data: str) -> None:
            if self.current is not None:
                self.current[3].append(data)

        def handle_endtag(self, tag: str) -> None:
            if self.current is not None and tag == self.current[0]:
                _, ja, en, parts = self.current
                self.elements.append((ja, en, "".join(parts)))
                self.current = None

    payload = _result([], status="partial")
    payload.pop("metadata")
    payload.pop("name")
    for language in ("ja", "en"):
        parser = LocalizedElements()
        parser.feed(render_html(payload, language))
        assert parser.language == language
        assert parser.selected == [language]
        assert parser.elements
        assert all(text == (ja if language == "ja" else en) for ja, en, text in parser.elements)
        assert any(ja == "スクリーニング結果" for ja, _, _ in parser.elements)
        assert any(ja == "結果はありません。" for ja, _, _ in parser.elements)
        assert any(ja.startswith("一部のデータを取得できませんでした") for ja, _, _ in parser.elements)


def test_cli_language_naming_override_and_overwrite(tmp_path: Path, capsys) -> None:
    source = _write(tmp_path, _result())
    before = source.read_bytes()
    assert main([str(source), "--format", "csv"]) == 0
    assert source.with_suffix(".csv").exists()
    assert "行を" in capsys.readouterr().out
    assert main([str(source), "--format", "csv", "--lang", "en"]) == 0
    english = tmp_path / "run.en.csv"
    assert english.exists()
    assert "Exported 1 rows" in capsys.readouterr().out
    with english.open(encoding="utf-8-sig", newline="") as stream:
        assert next(csv.reader(stream))[0] == "Symbol"
    assert main([str(source), "--format", "html", "--lang", "en"]) == 0
    assert '<html lang="en">' in (tmp_path / "run.en.html").read_text(encoding="utf-8")
    capsys.readouterr()
    explicit = tmp_path / "custom.html"
    args = [str(source), "--format", "html", "--lang", "en", "--output", str(explicit)]
    assert main(args) == 0
    assert explicit.exists()
    assert main(args) == 1
    assert "already exists" in capsys.readouterr().err
    assert main([*args, "--overwrite"]) == 0
    assert source.read_bytes() == before
