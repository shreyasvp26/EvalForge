"""Project request/response schemas — shape validation only."""

from __future__ import annotations

from datetime import datetime

from agent_eval_application.dto.project import ProjectDTO
from pydantic import BaseModel, ConfigDict, Field


class CreateProjectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    description: str = ""
    settings: dict[str, str] = Field(default_factory=dict)


class RenameProjectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)


class UpdateProjectSettingsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    settings: dict[str, str]


class ProjectResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    description: str
    status: str
    created_at: datetime
    settings: dict[str, str]

    @classmethod
    def from_dto(cls, dto: ProjectDTO) -> ProjectResponse:
        return cls(
            id=dto.id,
            name=dto.name,
            description=dto.description,
            status=dto.status,
            created_at=dto.created_at,
            settings=dict(dto.settings),
        )
