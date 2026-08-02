"""Agent and Adapter request/response schemas."""

from __future__ import annotations

from datetime import datetime

from agent_eval_application.dto.agent import (
    AdapterDTO,
    AdapterVersionDTO,
    AgentDTO,
    AgentVersionDTO,
)
from pydantic import BaseModel, ConfigDict, Field


class CreateAgentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    description: str = ""


class CreateAgentDraftVersionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1)
    release_notes: str = ""


class CreateAdapterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_id: str = Field(min_length=1)
    name: str = Field(min_length=1)


class CreateAdapterDraftVersionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1)
    notes: str = ""


class AgentVersionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    agent_id: str
    version_number: int
    status: str
    label: str
    release_notes: str
    predecessor_version_id: str | None
    created_at: datetime

    @classmethod
    def from_dto(cls, dto: AgentVersionDTO) -> AgentVersionResponse:
        return cls(
            id=dto.id,
            agent_id=dto.agent_id,
            version_number=dto.version_number,
            status=dto.status,
            label=dto.label,
            release_notes=dto.release_notes,
            predecessor_version_id=dto.predecessor_version_id,
            created_at=dto.created_at,
        )


class AgentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    description: str
    adapter_id: str | None
    status: str
    created_at: datetime
    active_version_id: str | None
    versions: list[AgentVersionResponse]

    @classmethod
    def from_dto(cls, dto: AgentDTO) -> AgentResponse:
        return cls(
            id=dto.id,
            name=dto.name,
            description=dto.description,
            adapter_id=dto.adapter_id,
            status=dto.status,
            created_at=dto.created_at,
            active_version_id=dto.active_version_id,
            versions=[AgentVersionResponse.from_dto(v) for v in dto.versions],
        )


class AdapterVersionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    adapter_id: str
    version_number: int
    status: str
    label: str
    notes: str
    predecessor_version_id: str | None
    created_at: datetime

    @classmethod
    def from_dto(cls, dto: AdapterVersionDTO) -> AdapterVersionResponse:
        return cls(
            id=dto.id,
            adapter_id=dto.adapter_id,
            version_number=dto.version_number,
            status=dto.status,
            label=dto.label,
            notes=dto.notes,
            predecessor_version_id=dto.predecessor_version_id,
            created_at=dto.created_at,
        )


class AdapterResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    agent_id: str
    name: str
    status: str
    created_at: datetime
    active_version_id: str | None
    versions: list[AdapterVersionResponse]

    @classmethod
    def from_dto(cls, dto: AdapterDTO) -> AdapterResponse:
        return cls(
            id=dto.id,
            agent_id=dto.agent_id,
            name=dto.name,
            status=dto.status,
            created_at=dto.created_at,
            active_version_id=dto.active_version_id,
            versions=[AdapterVersionResponse.from_dto(v) for v in dto.versions],
        )
