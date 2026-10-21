"""Filesystem and JSON syntax boundary for local definitions."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .errors import ConfigError

_SAFE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*\Z", re.ASCII)
_WINDOWS_RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}


def _reject_nonstandard_json_constant(value: str) -> None:
    """Reject NaN/Infinity values accepted by Python's permissive JSON decoder."""
    raise ValueError(f"non-standard JSON constant: {value}")


def definition_path(directory: Path, name: str, *, project_root: Path) -> Path:
    """Resolve one flat definition name, rejecting path and symlink escapes."""
    if not isinstance(name, str) or not _SAFE_NAME.fullmatch(name) or name.upper() in _WINDOWS_RESERVED:
        raise ConfigError("CONFIG_NAME_INVALID", "Invalid configuration name", "name")

    root = project_root.resolve()
    base = directory.resolve()
    if not base.is_relative_to(root):
        raise ConfigError("CONFIG_NAME_INVALID", "Invalid configuration path", "name")
    target = (base / f"{name}.json").resolve()
    if not target.is_relative_to(base):
        raise ConfigError("CONFIG_NAME_INVALID", "Invalid configuration name", "name")
    return target


def read_json(path: Path, *, kind: str) -> Any:
    """Read UTF-8 JSON without model-specific validation or console output."""
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ConfigError("CONFIG_FILE_NOT_FOUND", f"{kind} definition not found") from exc
    except OSError as exc:
        raise ConfigError("CONFIG_FILE_READ_ERROR", f"Cannot read {kind} definition") from exc
    except UnicodeError as exc:
        raise ConfigError("CONFIG_JSON_INVALID", f"Invalid {kind} JSON encoding") from exc

    try:
        return json.loads(content, parse_constant=_reject_nonstandard_json_constant)
    except (json.JSONDecodeError, ValueError) as exc:
        raise ConfigError("CONFIG_JSON_INVALID", f"Invalid {kind} JSON") from exc
