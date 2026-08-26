"""Platform catalog request and response schemas."""

from __future__ import annotations

from datetime import datetime

from agent_eval_application.dto.platform import PlatformDTO, PlatformVersionDTO
from pydantic import BaseModel, ConfigDict, Field


class CreatePlatformRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1)


class CreatePlatformDraftVersionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str = Field(min_length=1)
    sandbox_policy: dict[str, str] = Field(default_factory=dict)
    execution_policy: dict[str, str] = Field(default_factory=dict)
    timeout_policy: dict[str, str] = Field(default_factory=dict)
    environment_policy: dict[str, str] = Field(default_factory=dict)
    grading_policy: dict[str, str] = Field(default_factory=dict)
    notes: str = ""


class PlatformVersionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    platform_id: str
    version_number: int
    status: str
    label: str
    sandbox_policy: dict[str, str]
    execution_policy: dict[str, str]
    timeout_policy: dict[str, str]
    environment_policy: dict[str, str]
    grading_policy: dict[str, str]
    notes: str
    predecessor_version_id: str | None
    created_at: datetime

    @classmethod
    def from_dto(cls, dto: PlatformVersionDTO) -> PlatformVersionResponse:
        return cls(**{field: getattr(dto, field) for field in cls.model_fields})


class PlatformResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    name: str
    status: str
    created_at: datetime
    active_version_id: str | None
    versions: list[PlatformVersionResponse]

    @classmethod
    def from_dto(cls, dto: PlatformDTO) -> PlatformResponse:
        return cls(
            id=dto.id,
            name=dto.name,
            status=dto.status,
            created_at=dto.created_at,
            active_version_id=dto.active_version_id,
            versions=[
                PlatformVersionResponse.from_dto(version) for version in dto.versions
            ],
        )
