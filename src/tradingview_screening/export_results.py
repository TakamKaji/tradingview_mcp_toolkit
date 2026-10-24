"""Offline HTML/CSV views of saved JSON results; never contacts TradingView."""

from __future__ import annotations

import argparse
import csv
import html
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import quote

PREFERRED = (
    "symbol", "companyName", "name", "description", "volumeRank",
    "close", "change", "volume", "RSI", "RSI|60",
)

COLUMN_LABELS = {
    "symbol": ("銘柄コード", "Symbol"),
    "companyName": ("会社名", "Company"),
    "name": ("表示名", "Name"),
    "description": ("銘柄概要", "Description"),
    "close": ("終値", "Close"),
    "change": ("騰落率（%）", "Change (%)"),
    "volume": ("出来高", "Volume"),
    "volumeRank": ("出来高順位", "Volume rank"),
    "RSI": ("RSI", "RSI"),
    "RSI|60": ("RSI（1時間足）", "RSI (1h)"),
}

META_LABELS = (
    ("名前", "Name", "name"),
    ("処理", "Operation", "operation"),
    ("実行日時", "Executed", "executedAt"),
    ("状態", "Status", "status"),
    ("表示行数", "Displayed rows", "rowCount"),
    ("Provider総数", "Provider total", "totalCount"),
    ("全件取得", "Complete coverage", "completeCoverage"),
    ("上位件数", "Ranked top", "topCount"),
    ("一致件数", "Matched", "matchedCount"),
)

STATUS_LABELS = {
    "success": ("成功", "Success"),
    "partial": ("一部取得", "Partial"),
}


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(_value: str) -> None:
    raise ValueError("Invalid JSON constant")


def load_result(path: Path) -> dict[str, Any]:
    """Accept standard and custom results containing a tabular results array."""
    with path.open(encoding="utf-8") as stream:
        payload = json.load(
            stream, object_pairs_hook=_unique_object, parse_constant=_reject_constant,
        )
    if not isinstance(payload, dict):
        raise ValueError("Result must be a JSON object")  # noqa: TRY004
    if payload.get("status") not in {"success", "partial"}:
        raise ValueError("Only successful or partial results can be exported")
    rows = payload.get("results")
    if not isinstance(rows, list) or any(
        not isinstance(row, dict) or any(not isinstance(key, str) for key in row)
        for row in rows
    ):
        raise ValueError("Result must contain an array of objects in 'results'")
    return payload


def columns_for(rows: list[dict[str, Any]]) -> list[str]:
    found = set().union(*(set(row) for row in rows)) if rows else set()
    return [key for key in PREFERRED if key in found] + sorted(found - set(PREFERRED))


def _label(key: str, lang: str) -> str:
    return COLUMN_LABELS.get(key, (key, key))[lang == "en"]


def _csv_headers(columns: list[str], lang: str) -> list[str]:
    # Preserve unknown keys verbatim and disambiguate translated labels around them.
    used = {key for key in columns if key not in COLUMN_LABELS}
    headers = []
    for key in columns:
        if key not in COLUMN_LABELS:
            headers.append(key)
            continue
        base = _label(key, lang)
        candidate = base if base not in used else f"{base} [{key}]"
        number = 2
        while candidate in used:
            candidate = f"{base} [{key}] ({number})"
            number += 1
        used.add(candidate)
        headers.append(candidate)
    return headers


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False, allow_nan=False)
    if isinstance(value, bool):
        return str(value).lower()
    return str(value)


def _csv_cell(value: Any) -> str:
    text = _text(value)
    # Quoting CSV fields is not enough to prevent spreadsheet formula execution.
    if isinstance(value, str) and (
        text.lstrip().startswith(("=", "+", "-", "@"))
        or text.startswith(("\t", "\r", "\n"))
    ):
        return "'" + text
    return text


def _safe_csv_headers(columns: list[str], lang: str) -> list[str]:
    headers = _csv_headers(columns, lang)
    used = {header for header in headers if _csv_cell(header) == header}
    safe_headers = []
    for key, header in zip(columns, headers, strict=True):
        safe = _csv_cell(header)
        if safe != header:
            base = safe
            if safe in used:
                safe = f"{base} [{key}]"
            number = 2
            while safe in used:
                safe = f"{base} [{key}] ({number})"
                number += 1
            used.add(safe)
        safe_headers.append(safe)
    return safe_headers


def render_csv(payload: dict[str, Any], stream: Any, lang: str = "ja") -> None:
    rows = payload["results"]
    columns = columns_for(rows) or ["symbol"]
    writer = csv.writer(stream)
    writer.writerow(_safe_csv_headers(columns, lang))
    for row in rows:
        writer.writerow([_csv_cell(row.get(col)) for col in columns])


def _bilingual(ja: str, en: str, lang: str) -> str:
    return (
        f'<span data-ja="{html.escape(ja, quote=True)}" '
        f'data-en="{html.escape(en, quote=True)}">'
        f'{html.escape(ja if lang == "ja" else en)}</span>'
    )


def render_html(payload: dict[str, Any], lang: str = "ja") -> str:
    rows = payload["results"]
    columns = columns_for(rows) or ["symbol"]
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    values = {
        "name": payload.get("name"),
        "operation": payload.get("operation"),
        "executedAt": payload.get("executedAt"),
        "status": payload.get("status"),
        "rowCount": len(rows),
        "totalCount": metadata.get("totalCount"),
        "completeCoverage": metadata.get("completeCoverage"),
        "topCount": metadata.get("topCount"),
        "matchedCount": metadata.get("matchedCount"),
    }
    summary_fields = []
    for ja, en, key in META_LABELS:
        value = values[key]
        if value is None:
            continue
        if key == "status" and value in STATUS_LABELS:
            value_html = _bilingual(*STATUS_LABELS[value], lang)
        elif key == "completeCoverage" and isinstance(value, bool):
            value_html = _bilingual(
                "はい" if value else "いいえ", "Yes" if value else "No", lang,
            )
        else:
            value_html = html.escape(_text(value))
        summary_fields.append(f"{_bilingual(ja, en, lang)}: {value_html}")
    summary = " · ".join(summary_fields)
    ja_headers = _csv_headers(columns, "ja")
    en_headers = _csv_headers(columns, "en")
    header = "".join(
        f'<th scope="col">{_bilingual(ja, en, lang)}</th>'
        for ja, en in zip(ja_headers, en_headers, strict=True)
    )
    output_rows = []
    for row in rows:
        cells = []
        for column in columns:
            value = _text(row.get(column))
            escaped = html.escape(value, quote=True)
            if column == "symbol" and value:
                url = "https://www.tradingview.com/chart/?symbol=" + quote(value, safe="")
                escaped = (
                    f'<a href="{html.escape(url, quote=True)}" '
                    f'target="_blank" rel="noopener noreferrer">{escaped}</a>'
                )
            cells.append(f"<td>{escaped}</td>")
        output_rows.append("<tr>" + "".join(cells) + "</tr>")
    note = (
        ("一部のデータを取得できませんでした。全銘柄を網羅した結果ではありません。",
         "Partial result: some data was not retrieved; this is not a complete universe.")
        if payload["status"] == "partial" else
        ("保存された結果行のみを表示しています。市場全体を網羅するものではありません。",
         "This report shows returned rows only. It does not imply full market coverage.")
    )
    name = payload.get("name")
    title = html.escape(_text(name)) if name else _bilingual("スクリーニング結果", "Screening result", lang)
    page_title_ja = html.escape(_text(name or "スクリーニング結果") + " | TradingView MCP Support", quote=True)
    page_title_en = html.escape(_text(name or "Screening result") + " | TradingView MCP Support", quote=True)
    empty = _bilingual("結果はありません。", "No results.", lang)
    output_body = "".join(output_rows) or f'<tr><td colspan="{len(columns)}">{empty}</td></tr>'
    return f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title data-ja="{page_title_ja}" data-en="{page_title_en}">{page_title_ja if lang == "ja" else page_title_en}</title>
<style>
body{{font-family:system-ui,sans-serif;margin:2rem auto;max-width:1200px;padding:0 1rem;color:#1f2937}}
h1{{font-size:1.6rem}}.meta{{color:#475569;line-height:1.7}}
.note{{padding:.7rem 1rem;background:#f1f5f9;border-radius:6px}}
.language{{display:block;text-align:right;margin-bottom:1rem}}.language select{{font:inherit}}
.wrap{{overflow-x:auto}}table{{border-collapse:collapse;width:100%;font-size:.9rem}}
th,td{{padding:.55rem .7rem;border-bottom:1px solid #e2e8f0;text-align:left;white-space:nowrap}}
th{{background:#f8fafc;position:sticky;top:0}}tr:hover{{background:#f8fafc}}
a{{color:#0369a1}}
</style>
</head>
<body>
<label class="language">{_bilingual("表示言語", "Language", lang)}:
<select id="language" aria-label="Language">
<option value="ja"{' selected' if lang == 'ja' else ''}>日本語</option>
<option value="en"{' selected' if lang == 'en' else ''}>English</option>
</select></label>
<h1>{title}</h1>
<p class="meta">{summary}</p>
<p class="note">{_bilingual(*note, lang)}</p>
<div class="wrap"><table><thead><tr>{header}</tr></thead>
<tbody>{output_body}</tbody></table></div>
<p>{_bilingual('保存済みJSONからローカルで生成しました。TradingViewへのライブ通信は行っていません。', 'Generated locally from a saved JSON file; no live TradingView request was made.', lang)}</p>
<script>
document.getElementById('language').addEventListener('change', function (event) {{
  const lang = event.target.value;
  if (lang !== 'ja' && lang !== 'en') return;
  document.documentElement.lang = lang;
  document.querySelectorAll('[data-ja][data-en]').forEach(function (node) {{
    node.textContent = node.getAttribute('data-' + lang);
  }});
}});
</script>
</body></html>
"""


def export_file(
    source: Path, destination: Path, format_name: str, *, overwrite: bool, lang: str = "ja",
) -> int:
    if lang not in {"ja", "en"}:
        raise ValueError("Language must be ja or en")
    if not source.is_file():
        raise ValueError("Input JSON file does not exist")
    if destination == source or destination.resolve() == source.resolve():
        raise ValueError("Output must not overwrite the source JSON")
    if destination.is_symlink():
        raise ValueError("Output cannot be a symbolic link")
    if destination.exists() and not overwrite:
        raise FileExistsError("Output already exists (pass --overwrite to replace it)")
    if not destination.parent.is_dir():
        raise ValueError("Output directory does not exist")
    payload = load_result(source)
    suffix = ".csv" if format_name == "csv" else ".html"
    if destination.suffix.lower() != suffix:
        raise ValueError(f"Output filename must end with {suffix}")
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8-sig" if format_name == "csv" else "utf-8",
            newline="", dir=destination.parent, suffix=".tmp", delete=False,
        ) as output:
            temporary = Path(output.name)
            if format_name == "csv":
                render_csv(payload, output, lang)
            else:
                output.write(render_html(payload, lang))
            output.flush()
            os.fsync(output.fileno())
        if overwrite:
            os.replace(temporary, destination)
        else:
            os.link(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return len(payload["results"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Convert saved result JSON to offline CSV or HTML")
    parser.add_argument("input", type=Path, help="Existing result JSON path")
    parser.add_argument("--format", choices=("csv", "html"), required=True)
    parser.add_argument("--lang", choices=("ja", "en"), default="ja", help="Export language")
    parser.add_argument("--output", type=Path, help="Destination (default: same path with new extension)")
    parser.add_argument("--overwrite", action="store_true", help="Replace an existing export file")
    args = parser.parse_args(argv)
    source: Path = args.input
    destination: Path = args.output or source.with_suffix(
        (".en" if args.lang == "en" else "") + "." + args.format,
    )
    try:
        count = export_file(source, destination, args.format, overwrite=args.overwrite, lang=args.lang)
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
        prefix = "出力に失敗しました" if args.lang == "ja" else "Export failed"
        print(f"{prefix}: {exc}", file=sys.stderr)
        return 1
    if args.lang == "ja":
        print(f"{count}行を{destination}に出力しました")
    else:
        print(f"Exported {count} rows to {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
