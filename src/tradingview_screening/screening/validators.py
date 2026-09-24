"""Screening model validation and loading."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import ValidationError

from tradingview_screening.common.config import definition_path, read_json
from tradingview_screening.common.errors import ConfigError

from .schema import ScreeningDefinition


def validate_screening(data: Any) -> ScreeningDefinition:
    try:
        return ScreeningDefinition.model_validate(data)
    except ValidationError as exc:
        field = ".".join(str(part) for part in exc.errors()[0]["loc"]) or None
        raise ConfigError("CONFIG_VALIDATION_ERROR", "Invalid screening definition", field) from exc


def load_screening(path: Path) -> ScreeningDefinition:
    return validate_screening(read_json(path, kind="screening"))


def load_screening_by_name(name: str, project_root: Path) -> ScreeningDefinition:
    return load_screening(
        definition_path(project_root / "screenings", name, project_root=project_root)
    )
