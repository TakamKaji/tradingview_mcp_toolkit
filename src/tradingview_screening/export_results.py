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
        raise ValueError("Result must be a JSON object")
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
    if text.lstrip().startswith(("=", "+", "-", "@")) or text.startswith(("\t", "\r", "\n")):
        return "'" + text
    return text


def render_csv(payload: dict[str, Any], stream: Any) -> None:
    rows = payload["results"]
    columns = columns_for(rows) or ["symbol"]
    writer = csv.writer(stream)
    writer.writerow(columns)
    for row in rows:
        writer.writerow([_csv_cell(row.get(col)) for col in columns])


def render_html(payload: dict[str, Any]) -> str:
    rows = payload["results"]
    columns = columns_for(rows) or ["symbol"]
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    fields = [
        ("Name", payload.get("name")),
        ("Operation", payload.get("operation")),
        ("Executed", payload.get("executedAt")),
        ("Status", payload.get("status")),
        ("Displayed rows", len(rows)),
        ("Provider total", metadata.get("totalCount")),
        ("Complete coverage", metadata.get("completeCoverage")),
        ("Ranked top", metadata.get("topCount")),
        ("Matched", metadata.get("matchedCount")),
    ]
    summary = " · ".join(
        f"{html.escape(label)}: {html.escape(_text(value))}"
        for label, value in fields if value is not None
    )
    header = "".join(f"<th scope=\"col\">{html.escape(column)}</th>" for column in columns)
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
        "Partial result: some data was not retrieved; this is not a complete universe."
        if payload["status"] == "partial" else
        "This report shows returned rows only. It does not imply full market coverage."
    )
    title = html.escape(_text(payload.get("name") or "Screening result"))
    return f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} | TradingView MCP Support</title>
<style>
body{{font-family:system-ui,sans-serif;margin:2rem auto;max-width:1200px;padding:0 1rem;color:#1f2937}}
h1{{font-size:1.6rem}}.meta{{color:#475569;line-height:1.7}}
.note{{padding:.7rem 1rem;background:#f1f5f9;border-radius:6px}}
.wrap{{overflow-x:auto}}table{{border-collapse:collapse;width:100%;font-size:.9rem}}
th,td{{padding:.55rem .7rem;border-bottom:1px solid #e2e8f0;text-align:left;white-space:nowrap}}
th{{background:#f8fafc;position:sticky;top:0}}tr:hover{{background:#f8fafc}}
a{{color:#0369a1}}
</style>
</head>
<body>
<h1>{title}</h1>
<p class="meta">{summary}</p>
<p class="note">{html.escape(note)}</p>
<div class="wrap"><table><thead><tr>{header}</tr></thead>
<tbody>{''.join(output_rows)}</tbody></table></div>
<p>Generated locally from a saved JSON file; no live TradingView request was made.</p>
</body></html>
"""


def export_file(source: Path, destination: Path, format_name: str, *, overwrite: bool) -> int:
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
                render_csv(payload, output)
            else:
                output.write(render_html(payload))
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
    parser.add_argument("--output", type=Path, help="Destination (default: same path with new extension)")
    parser.add_argument("--overwrite", action="store_true", help="Replace an existing export file")
    args = parser.parse_args(argv)
    source: Path = args.input
    destination: Path = args.output or source.with_suffix("." + args.format)
    try:
        count = export_file(source, destination, args.format, overwrite=args.overwrite)
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
        print(f"Export failed: {exc}", file=sys.stderr)
        return 1
    print(f"Exported {count} rows to {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
