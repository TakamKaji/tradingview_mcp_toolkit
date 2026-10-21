"""Read-only comparison of two saved screening observations."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tradingview_screening.integrations.tradingview.watchlist_normalization import (
    valid_watchlist_symbol,
)

from .results import _executed_at, _scan_results, _valid_fingerprint


def _reference(item: Any, root: Path) -> dict[str, Any]:
    metadata = item.payload["metadata"]
    fingerprint = metadata.get("definitionFingerprint")
    return {
        "file": item.path.relative_to(root).as_posix(),
        "executedAt": item.payload["executedAt"],
        "returnedCount": metadata["returnedCount"],
        "totalCount": metadata.get("totalCount"),
        "completeCoverage": metadata.get("completeCoverage"),
        "definitionFingerprint": fingerprint if _valid_fingerprint(fingerprint) else None,
    }


def _row_map(rows: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]] | None, str | None]:
    mapped: dict[str, dict[str, Any]] = {}
    for row in rows:
        symbol = row["symbol"]
        if not valid_watchlist_symbol(symbol) or symbol in mapped:
            return None, "INVALID_SYMBOLS"
        if any(
            value is not None and type(value) not in {str, int, float, bool}
            for value in row.values()
        ):
            return None, "INVALID_VALUES"
        mapped[symbol] = row
    return mapped, None


def _changed(before: Any, after: Any) -> bool:
    return (type(before) is bool) != (type(after) is bool) or before != after


def _field(row: dict[str, Any], key: str) -> dict[str, Any]:
    if key not in row:
        return {"present": False}
    return {"present": True, "value": row[key]}


def compare_results(project_root: Path, name: str) -> dict[str, Any]:
    """Compare the two newest success snapshots; never fall back after a mismatch."""
    snapshots = [
        item for item in _scan_results(
            project_root, name, validate_fingerprint=False, validate_uniqueness=False,
        ) if item.payload["status"] == "success"
    ][:2]
    envelope: dict[str, Any] = {
        "schemaVersion": 1, "status": "not_comparable", "operation": "screening_compare",
        "name": name, "from": None, "to": None, "fingerprintMatched": None,
    }
    if snapshots:
        envelope["to"] = _reference(snapshots[0], project_root)
    if len(snapshots) < 2:
        envelope["reason"] = "NO_BASELINE"
        return envelope
    newer, older = snapshots
    envelope["from"] = _reference(older, project_root)
    metadata = [item.payload["metadata"] for item in (older, newer)]
    if any("definitionFingerprint" not in value for value in metadata):
        envelope["reason"] = "MISSING_FINGERPRINT"
        return envelope
    fingerprints = [value["definitionFingerprint"] for value in metadata]
    if not all(_valid_fingerprint(value) for value in fingerprints):
        envelope["reason"] = "INVALID_FINGERPRINT"
        return envelope
    if any(value["version"] != 1 or value["algorithm"] != "sha256" for value in fingerprints):
        envelope["reason"] = "UNSUPPORTED_FINGERPRINT"
        return envelope
    if fingerprints[0] != fingerprints[1]:
        envelope["fingerprintMatched"] = False
        envelope["reason"] = "DEFINITION_MISMATCH"
        return envelope
    envelope["fingerprintMatched"] = True
    old_rows, old_error = _row_map(older.payload["results"])
    new_rows, new_error = _row_map(newer.payload["results"])
    if old_error or new_error:
        envelope["reason"] = old_error or new_error
        return envelope
    if any(_executed_at(item.payload, name=name) is None for item in (older, newer)):
        envelope["reason"] = "INVALID_METADATA"
        return envelope
    assert old_rows is not None and new_rows is not None
    old_symbols, new_symbols = set(old_rows), set(new_rows)
    common = sorted(old_symbols & new_symbols)
    changes = []
    for symbol in common:
        before, after = old_rows[symbol], new_rows[symbol]
        fields = {}
        for key in sorted((before.keys() | after.keys()) - {"symbol"}):
            if key not in before or key not in after or _changed(before[key], after[key]):
                fields[key] = {"before": _field(before, key), "after": _field(after, key)}
        if fields:
            changes.append({"symbol": symbol, "fields": fields})
    old_total = older.payload["metadata"].get("totalCount")
    new_total = newer.payload["metadata"].get("totalCount")
    envelope.update({
        "status": "success",
        "comparisonScope": (
            "full_matched_set" if (
                older.payload["metadata"].get("completeCoverage") is True
                and newer.payload["metadata"].get("completeCoverage") is True
            ) else "observed_set_only"
        ),
        "observedAdded": sorted(new_symbols - old_symbols),
        "observedRemoved": sorted(old_symbols - new_symbols),
        "observedCommon": common,
        "indicatorChanges": changes,
        "totalCountChange": new_total - old_total if old_total is not None and new_total is not None else None,
    })
    return envelope
