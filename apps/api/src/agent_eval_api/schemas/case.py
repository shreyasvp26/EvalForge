"""Case and Prompt request/response schemas."""

from __future__ import annotations

from datetime import datetime

from agent_eval_application.dto.case import CaseDTO, CaseVersionDTO, PromptVersionDTO
from pydantic import BaseModel, ConfigDict, Field


class CreateCaseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str = ""
    category: str = ""
    difficulty: str = ""
    language: str = ""
    tags: list[str] = Field(default_factory=list)


class CreatePromptDraftVersionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1)


class CreateCaseDraftVersionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str = Field(min_length=1)
    repository_url: str = Field(min_length=1)
    commit_sha: str = Field(min_length=1)
    expected_checks: list[str] = Field(default_factory=list)
    applicable_grader_ids: list[str] = Field(default_factory=list)
    prompt_version_id: str = Field(min_length=1)
    subdirectory: str | None = None


class PromptVersionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    prompt_id: str
    version_number: int
    status: str
    content: str
    predecessor_version_id: str | None
    created_at: datetime

    @classmethod
    def from_dto(cls, dto: PromptVersionDTO) -> PromptVersionResponse:
        return cls(
            id=dto.id,
            prompt_id=dto.prompt_id,
            version_number=dto.version_number,
            status=dto.status,
            content=dto.content,
            predecessor_version_id=dto.predecessor_version_id,
            created_at=dto.created_at,
        )


class CaseVersionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    case_id: str
    version_number: int
    status: str
    description: str
    repository_url: str
    commit_sha: str
    subdirectory: str | None
    expected_checks: list[str]
    applicable_grader_ids: list[str]
    prompt_version_id: str
    predecessor_version_id: str | None
    created_at: datetime

    @classmethod
    def from_dto(cls, dto: CaseVersionDTO) -> CaseVersionResponse:
        return cls(
            id=dto.id,
            case_id=dto.case_id,
            version_number=dto.version_number,
            status=dto.status,
            description=dto.description,
            repository_url=dto.repository_url,
            commit_sha=dto.commit_sha,
            subdirectory=dto.subdirectory,
            expected_checks=list(dto.expected_checks),
            applicable_grader_ids=list(dto.applicable_grader_ids),
            prompt_version_id=dto.prompt_version_id,
            predecessor_version_id=dto.predecessor_version_id,
            created_at=dto.created_at,
        )


class CaseResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    project_id: str
    prompt_id: str
    name: str
    description: str
    category: str = ""
    difficulty: str = ""
    language: str = ""
    tags: list[str] = Field(default_factory=list)
    status: str
    created_at: datetime
    active_version_id: str | None
    active_prompt_version_id: str | None
    versions: list[CaseVersionResponse]
    prompt_versions: list[PromptVersionResponse]

    @classmethod
    def from_dto(cls, dto: CaseDTO) -> CaseResponse:
        return cls(
            id=dto.id,
            project_id=dto.project_id,
            prompt_id=dto.prompt_id,
            name=dto.name,
            description=dto.description,
            category=dto.category,
            difficulty=dto.difficulty,
            language=dto.language,
            tags=list(dto.tags),
            status=dto.status,
            created_at=dto.created_at,
            active_version_id=dto.active_version_id,
            active_prompt_version_id=dto.active_prompt_version_id,
            versions=[CaseVersionResponse.from_dto(v) for v in dto.versions],
            prompt_versions=[
                PromptVersionResponse.from_dto(v) for v in dto.prompt_versions
            ],
        )
