"""Pydantic contract for one screening definition."""

from __future__ import annotations

import math
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictFloat,
    StrictInt,
    StrictStr,
    field_validator,
    model_validator,
)

Number = StrictInt | StrictFloat
Range = tuple[Number | None, Number | None]
NonEmptyString = Annotated[StrictStr, Field(min_length=1)]


class WatchlistConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: StrictBool
    name: StrictStr | None = None

    @field_validator("name")
    @classmethod
    def nonblank_name(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("name must not be empty")
        return value

    @model_validator(mode="after")
    def enabled_requires_name(self) -> WatchlistConfig:
        if self.enabled and self.name is None:
            raise ValueError("enabled watchlist requires name")
        return self


class ScreeningDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schemaVersion: StrictInt
    name: NonEmptyString
    description: StrictStr | None = None
    market: NonEmptyString
    symbolTypes: list[NonEmptyString] = Field(min_length=1)
    filters: dict[NonEmptyString, Range] = Field(default_factory=dict)
    sortBy: StrictStr | None = None
    sortOrder: Literal["asc", "desc"] = "desc"
    limit: StrictInt = Field(ge=1, le=1000)
    columns: list[NonEmptyString] = Field(min_length=1)
    watchlist: WatchlistConfig | None = None

    @field_validator("schemaVersion")
    @classmethod
    def valid_schema_version(cls, value: int) -> int:
        if value != 1:
            raise ValueError("schemaVersion must be 1")
        return value

    @field_validator("name", "market", "symbolTypes", "columns")
    @classmethod
    def reject_blank(cls, value: str | list[str]) -> str | list[str]:
        values = [value] if isinstance(value, str) else value
        if any(not item.strip() for item in values):
            raise ValueError("value must not be empty")
        return value

    @field_validator("sortBy")
    @classmethod
    def reject_blank_sort(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("sortBy must not be empty")
        return value

    @field_validator("filters")
    @classmethod
    def validate_filters(cls, value: dict[str, Range]) -> dict[str, Range]:
        for field, (minimum, maximum) in value.items():
            if not field.strip():
                raise ValueError("filter field must not be empty")
            if minimum is None and maximum is None:
                raise ValueError(f"filter {field} requires a bound")
            if any(isinstance(bound, float) and not math.isfinite(bound) for bound in (minimum, maximum)):
                raise ValueError(f"filter {field} requires finite bounds")
            if minimum is not None and maximum is not None and minimum > maximum:
                raise ValueError(f"filter {field} minimum exceeds maximum")
        return value
