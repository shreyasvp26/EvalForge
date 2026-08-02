"""Run request/response schemas."""

from __future__ import annotations

from datetime import datetime

from agent_eval_application.dto.run import RunDTO
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


class ScoreResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    grader_id: str
    grader_version_id: str
    value: ScoreValueResponse
    explanation_artifact_id: str | None


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
            scores=[
                ScoreResponse(
                    id=s.id,
                    grader_id=s.grader_id,
                    grader_version_id=s.grader_version_id,
                    value=ScoreValueResponse(
                        numeric=s.value.numeric,
                        categorical=s.value.categorical,
                        passed=s.value.passed,
                    ),
                    explanation_artifact_id=s.explanation_artifact_id,
                )
                for s in dto.scores
            ],
        )
