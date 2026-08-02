"""Suite request/response schemas."""

from __future__ import annotations

from datetime import datetime

from agent_eval_application.dto.suite import SuiteDTO, SuiteVersionDTO
from pydantic import BaseModel, ConfigDict, Field


class CreateSuiteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str = ""


class SuiteCompositionEntryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_version_id: str = Field(min_length=1)
    position: int = Field(ge=0)
    case_project_id: str = Field(min_length=1)


class CreateSuiteDraftVersionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    composition: list[SuiteCompositionEntryRequest] = Field(min_length=1)


class SuiteCompositionEntryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_version_id: str
    position: int
    case_project_id: str


class SuiteVersionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    suite_id: str
    version_number: int
    status: str
    composition: list[SuiteCompositionEntryResponse]
    predecessor_version_id: str | None
    created_at: datetime

    @classmethod
    def from_dto(cls, dto: SuiteVersionDTO) -> SuiteVersionResponse:
        return cls(
            id=dto.id,
            suite_id=dto.suite_id,
            version_number=dto.version_number,
            status=dto.status,
            composition=[
                SuiteCompositionEntryResponse(
                    case_version_id=e.case_version_id,
                    position=e.position,
                    case_project_id=e.case_project_id,
                )
                for e in dto.composition
            ],
            predecessor_version_id=dto.predecessor_version_id,
            created_at=dto.created_at,
        )


class SuiteResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    project_id: str
    name: str
    description: str
    status: str
    created_at: datetime
    active_version_id: str | None
    versions: list[SuiteVersionResponse]

    @classmethod
    def from_dto(cls, dto: SuiteDTO) -> SuiteResponse:
        return cls(
            id=dto.id,
            project_id=dto.project_id,
            name=dto.name,
            description=dto.description,
            status=dto.status,
            created_at=dto.created_at,
            active_version_id=dto.active_version_id,
            versions=[SuiteVersionResponse.from_dto(v) for v in dto.versions],
        )
