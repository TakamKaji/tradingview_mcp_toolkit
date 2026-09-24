"""Small, stable errors for configuration consumers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ConfigErrorCode = Literal[
    "CONFIG_FILE_NOT_FOUND",
    "CONFIG_JSON_INVALID",
    "CONFIG_VALIDATION_ERROR",
    "CONFIG_REFERENCE_NOT_FOUND",
    "CONFIG_NAME_INVALID",
    "CONFIG_FILE_READ_ERROR",
]


@dataclass
class ConfigError(Exception):
    code: ConfigErrorCode
    message: str
    field: str | None = None

    def __str__(self) -> str:
        return self.message

    def to_dict(self) -> dict[str, str]:
        result = {"code": self.code, "message": self.message}
        if self.field is not None:
            result["field"] = self.field
        return result


class TransientRequestError(Exception):
    """Provider-independent marker for a temporary communication failure."""
