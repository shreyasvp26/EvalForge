"""Health and system schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str


class ReadyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    checks: dict[str, str]


class SystemInfoResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service: str
    version: str
    api_version: str
    environment: str
