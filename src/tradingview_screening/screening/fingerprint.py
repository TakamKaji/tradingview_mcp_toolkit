"""Stable identity for the selectors that produced a screening result."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .schema import ScreeningDefinition

SELECTORS = (
    "market", "symbolTypes", "filters", "filterPreset", "symbolset",
    "sortBy", "sortOrder", "limit", "columns",
)


def definition_fingerprint(screening: ScreeningDefinition) -> dict[str, Any]:
    """Hash all nine selectors, including their validated defaults."""
    definition = screening.model_dump(mode="json")
    selectors = {key: definition[key] for key in SELECTORS}
    canonical = json.dumps(
        selectors, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False,
    ).encode("utf-8")
    return {"version": 1, "algorithm": "sha256", "value": hashlib.sha256(canonical).hexdigest()}
