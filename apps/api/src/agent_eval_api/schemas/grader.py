"""Grader request/response schemas."""

from __future__ import annotations

from datetime import datetime

from agent_eval_application.dto.grader import GraderDTO, GraderVersionDTO
from pydantic import BaseModel, ConfigDict, Field


class CreateGraderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    family: str = Field(min_length=1)
    description: str = ""


class CreateGraderDraftVersionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1)
    specification: str = Field(min_length=1)


class GraderVersionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    grader_id: str
    version_number: int
    status: str
    label: str
    specification: str
    predecessor_version_id: str | None
    created_at: datetime

    @classmethod
    def from_dto(cls, dto: GraderVersionDTO) -> GraderVersionResponse:
        return cls(
            id=dto.id,
            grader_id=dto.grader_id,
            version_number=dto.version_number,
            status=dto.status,
            label=dto.label,
            specification=dto.specification,
            predecessor_version_id=dto.predecessor_version_id,
            created_at=dto.created_at,
        )


class GraderResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    family: str
    description: str
    status: str
    created_at: datetime
    active_version_id: str | None
    versions: list[GraderVersionResponse]

    @classmethod
    def from_dto(cls, dto: GraderDTO) -> GraderResponse:
        return cls(
            id=dto.id,
            name=dto.name,
            family=dto.family,
            description=dto.description,
            status=dto.status,
            created_at=dto.created_at,
            active_version_id=dto.active_version_id,
            versions=[GraderVersionResponse.from_dto(v) for v in dto.versions],
        )
