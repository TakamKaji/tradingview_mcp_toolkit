"""Job loading and screening reference checks."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import ValidationError

from tradingview_screening.common.config import definition_path, read_json
from tradingview_screening.common.errors import ConfigError
from tradingview_screening.screening.schema import ScreeningDefinition
from tradingview_screening.screening.validators import load_screening_by_name

from .schema import JobDefinition


def validate_job(data: Any) -> JobDefinition:
    try:
        return JobDefinition.model_validate(data)
    except ValidationError as exc:
        field = ".".join(str(part) for part in exc.errors()[0]["loc"]) or None
        raise ConfigError("CONFIG_VALIDATION_ERROR", "Invalid job definition", field) from exc


def load_job(path: Path) -> JobDefinition:
    return validate_job(read_json(path, kind="job"))


def load_job_by_name(name: str, project_root: Path) -> JobDefinition:
    job = load_job(definition_path(project_root / "jobs", name, project_root=project_root))
    if job.name != name:
        raise ConfigError(
            "CONFIG_VALIDATION_ERROR",
            "Job name does not match filename",
            "name",
        )
    return job


def validate_job_screening_reference(
    job: JobDefinition, project_root: Path
) -> ScreeningDefinition | None:
    """Validate a screening reference; builtin tasks have no screening reference."""
    if job.task.type == "builtin":
        return None
    try:
        return load_screening_by_name(job.task.definition, project_root)
    except ConfigError as exc:
        if exc.code == "CONFIG_FILE_NOT_FOUND":
            raise ConfigError(
                "CONFIG_REFERENCE_NOT_FOUND", "Referenced screening definition not found", "task.definition"
            ) from exc
        raise
