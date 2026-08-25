"""Run request/response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from agent_eval_application.dto.run import (
    ArtifactDTO,
    ExecutionEventDTO,
    RunDTO,
    ScoreDTO,
)
from pydantic import BaseModel, ConfigDict, Field


class GraderVersionRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    grader_id: str = Field(min_length=1)
    grader_version_id: str = Field(min_length=1)


class CreateRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    case_version_id: str = Field(min_length=1)
    prompt_version_id: str = Field(min_length=1)
    agent_id: str = Field(min_length=1)
    agent_version_id: str = Field(min_length=1)
    adapter_version_id: str = Field(min_length=1)
    grader_version_refs: list[GraderVersionRef] = Field(min_length=1)
    platform_version_id: str = Field(min_length=1)
    suite_id: str | None = None
    suite_version_id: str | None = None


class CancelRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str | None = None


class RunPinsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str
    case_version_id: str
    prompt_version_id: str
    agent_version_id: str
    adapter_version_id: str
    platform_version_id: str
    grader_version_ids: list[str]
    suite_version_id: str | None


class ScoreValueResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    numeric: float | None
    categorical: str | None
    passed: bool | None
    detail: dict[str, Any] = Field(default_factory=dict)


class ScoreResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    grader_id: str
    grader_version_id: str
    value: ScoreValueResponse
    explanation_artifact_id: str | None

    @classmethod
    def from_dto(cls, dto: ScoreDTO) -> ScoreResponse:
        return cls(
            id=dto.id,
            grader_id=dto.grader_id,
            grader_version_id=dto.grader_version_id,
            value=ScoreValueResponse(
                numeric=dto.value.numeric,
                categorical=dto.value.categorical,
                passed=dto.value.passed,
                detail=dict(dto.value.detail),
            ),
            explanation_artifact_id=dto.explanation_artifact_id,
        )


class ExecutionEventResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    run_id: str
    sequence: int
    kind: str
    action: dict[str, Any]
    artifact_ids: list[str]
    occurred_at: datetime
    metadata: dict[str, str]

    @classmethod
    def from_dto(cls, dto: ExecutionEventDTO) -> ExecutionEventResponse:
        return cls(
            id=dto.id,
            run_id=dto.run_id,
            sequence=dto.sequence,
            kind=dto.kind,
            action=dict(dto.action),
            artifact_ids=list(dto.artifact_ids),
            occurred_at=dto.occurred_at,
            metadata=dict(dto.metadata),
        )


class ArtifactResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    run_id: str
    kind: str
    storage_key: str
    content_type: str
    size_bytes: int
    checksum: str
    created_at: datetime
    produced_by_grader_version_id: str | None

    @classmethod
    def from_dto(cls, dto: ArtifactDTO) -> ArtifactResponse:
        return cls(
            id=dto.id,
            run_id=dto.run_id,
            kind=dto.kind,
            storage_key=dto.storage_key,
            content_type=dto.content_type,
            size_bytes=dto.size_bytes,
            checksum=dto.checksum,
            created_at=dto.created_at,
            produced_by_grader_version_id=dto.produced_by_grader_version_id,
        )


class RunResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    status: str
    created_at: datetime
    pins: RunPinsResponse
    failure_reason: str | None
    cancellation_reason: str | None
    sandbox_id: str | None
    expected_grader_count: int
    produced_score_count: int
    is_partially_graded: bool
    scores: list[ScoreResponse]

    @classmethod
    def from_dto(cls, dto: RunDTO) -> RunResponse:
        return cls(
            id=dto.id,
            status=dto.status,
            created_at=dto.created_at,
            pins=RunPinsResponse(
                project_id=dto.pins.project_id,
                case_version_id=dto.pins.case_version_id,
                prompt_version_id=dto.pins.prompt_version_id,
                agent_version_id=dto.pins.agent_version_id,
                adapter_version_id=dto.pins.adapter_version_id,
                platform_version_id=dto.pins.platform_version_id,
                grader_version_ids=list(dto.pins.grader_version_ids),
                suite_version_id=dto.pins.suite_version_id,
            ),
            failure_reason=dto.failure_reason,
            cancellation_reason=dto.cancellation_reason,
            sandbox_id=dto.sandbox_id,
            expected_grader_count=dto.expected_grader_count,
            produced_score_count=dto.produced_score_count,
            is_partially_graded=dto.is_partially_graded,
            scores=[ScoreResponse.from_dto(s) for s in dto.scores],
        )
