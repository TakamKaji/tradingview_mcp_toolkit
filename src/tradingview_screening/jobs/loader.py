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


def list_job_names(project_root: Path) -> tuple[str, ...]:
    """Return safe flat Job definition names in deterministic order."""
    directory = project_root / "jobs"
    try:
        root = project_root.resolve()
        base = directory.resolve()
        if directory.is_symlink() or not base.is_relative_to(root):
            raise ConfigError("CONFIG_NAME_INVALID", "Invalid job definition path", "name")
        entries = tuple(directory.iterdir())
    except FileNotFoundError:
        return ()
    except OSError as exc:
        raise ConfigError("CONFIG_FILE_READ_ERROR", "Cannot read job definitions") from exc

    names: list[str] = []
    for path in entries:
        if path.suffix != ".json":
            continue
        if path.is_symlink() or not path.is_file():
            raise ConfigError("CONFIG_NAME_INVALID", "Invalid job definition path", "name")
        name = path.stem
        expected = definition_path(directory, name, project_root=project_root)
        if path.resolve() != expected:
            raise ConfigError("CONFIG_NAME_INVALID", "Invalid job definition path", "name")
        names.append(name)
    return tuple(sorted(names))


def load_job_by_name(name: str, project_root: Path) -> JobDefinition:
    directory = project_root / "jobs"
    resolved = definition_path(directory, name, project_root=project_root)
    path = directory / f"{name}.json"
    if directory.is_symlink() or path.is_symlink():
        raise ConfigError("CONFIG_NAME_INVALID", "Invalid job definition path", "name")
    job = load_job(resolved)
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
        screening = load_screening_by_name(job.task.definition, project_root)
        if screening.name != job.task.definition:
            raise ConfigError(
                "CONFIG_VALIDATION_ERROR", "Screening name does not match filename", "task.definition"
            )
        return screening
    except ConfigError as exc:
        if exc.code == "CONFIG_FILE_NOT_FOUND":
            raise ConfigError(
                "CONFIG_REFERENCE_NOT_FOUND", "Referenced screening definition not found", "task.definition"
            ) from exc
        raise
