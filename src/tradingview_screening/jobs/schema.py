"""Pydantic contract for one scheduled job."""

from __future__ import annotations

import re
from typing import Annotated, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    StrictStr,
    field_validator,
)

NonEmptyString = Annotated[StrictStr, Field(min_length=1)]
_TIME = re.compile(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]\Z", re.ASCII)


class JobTask(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["screening", "builtin"]
    definition: NonEmptyString

    @field_validator("definition")
    @classmethod
    def reject_blank_definition(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("definition must not be empty")
        return value


class JobSchedule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["daily"]
    time: StrictStr
    timezone: StrictStr

    @field_validator("time")
    @classmethod
    def valid_time(cls, value: str) -> str:
        if not _TIME.fullmatch(value):
            raise ValueError("time must use 24-hour HH:MM")
        return value

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value: str) -> str:
        if not value or value.startswith("/") or "\\" in value or ".." in value:
            raise ValueError("timezone must be an IANA timezone")
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError, KeyError) as exc:
            raise ValueError("timezone must be an IANA timezone") from exc
        return value


class JobOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    save: StrictBool
    watchlistSync: StrictBool


class JobDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schemaVersion: StrictInt
    name: NonEmptyString
    enabled: StrictBool
    task: JobTask
    schedule: JobSchedule
    output: JobOutput

    @field_validator("schemaVersion")
    @classmethod
    def valid_schema_version(cls, value: int) -> int:
        if value != 1:
            raise ValueError("schemaVersion must be 1")
        return value

    @field_validator("name")
    @classmethod
    def reject_blank_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("name must not be empty")
        return value
