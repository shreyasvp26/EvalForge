"""Suite request/response schemas."""

from __future__ import annotations

from datetime import datetime

from agent_eval_application.dto.suite import SuiteDTO, SuiteVersionDTO
from agent_eval_application.dto.suite_execution import (
    SuiteAggregateDTO,
    SuiteExecutionDTO,
)
from pydantic import BaseModel, ConfigDict, Field

from agent_eval_api.schemas.run import (
    GraderVersionRef,
    RunResponse,
    ScoreAggregateResponse,
)


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


class CreateSuiteRunsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_id: str = Field(min_length=1)
    agent_version_id: str = Field(min_length=1)
    adapter_version_id: str = Field(min_length=1)
    platform_version_id: str = Field(min_length=1)
    grader_version_refs: list[GraderVersionRef] | None = None


class SuiteRunEntryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_version_id: str
    position: int
    run: RunResponse
    aggregate: ScoreAggregateResponse


class SuiteExecutionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    suite_id: str
    suite_version_id: str
    total_cases: int
    runs: list[SuiteRunEntryResponse]

    @classmethod
    def from_dto(cls, dto: SuiteExecutionDTO) -> SuiteExecutionResponse:
        return cls(
            suite_id=dto.suite_id,
            suite_version_id=dto.suite_version_id,
            total_cases=dto.total_cases,
            runs=[
                SuiteRunEntryResponse(
                    case_version_id=entry.case_version_id,
                    position=entry.position,
                    run=RunResponse.from_dto(entry.run),
                    aggregate=ScoreAggregateResponse(
                        passed=entry.aggregate.passed,
                        overall_score=entry.aggregate.overall_score,
                        objective_failed=entry.aggregate.objective_failed,
                        score_count=entry.aggregate.score_count,
                        reason=entry.aggregate.reason,
                    ),
                )
                for entry in dto.runs
            ],
        )


class SuiteCaseResultResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_version_id: str
    run_id: str
    status: str
    aggregate: ScoreAggregateResponse
    failure_reason: str | None
    failure_category: str | None = None


class SuiteAggregateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    suite_id: str
    suite_version_id: str
    total_cases: int
    run_count: int
    completed: int
    failed: int
    execution_failed: int
    cancelled: int
    queued_or_running: int
    passed: int
    evaluation_failed: int
    objective_failed_count: int
    pass_rate: float | None
    average_score: float | None
    cases: list[SuiteCaseResultResponse]

    @classmethod
    def from_dto(cls, dto: SuiteAggregateDTO) -> SuiteAggregateResponse:
        return cls(
            suite_id=dto.suite_id,
            suite_version_id=dto.suite_version_id,
            total_cases=dto.total_cases,
            run_count=dto.run_count,
            completed=dto.completed,
            failed=dto.failed,
            execution_failed=dto.execution_failed,
            cancelled=dto.cancelled,
            queued_or_running=dto.queued_or_running,
            passed=dto.passed,
            evaluation_failed=dto.evaluation_failed,
            objective_failed_count=dto.objective_failed_count,
            pass_rate=dto.pass_rate,
            average_score=dto.average_score,
            cases=[
                SuiteCaseResultResponse(
                    case_version_id=c.case_version_id,
                    run_id=c.run_id,
                    status=c.status,
                    aggregate=ScoreAggregateResponse(
                        passed=c.aggregate.passed,
                        overall_score=c.aggregate.overall_score,
                        objective_failed=c.aggregate.objective_failed,
                        score_count=c.aggregate.score_count,
                        reason=c.aggregate.reason,
                    ),
                    failure_reason=c.failure_reason,
                    failure_category=c.failure_category,
                )
                for c in dto.cases
            ],
        )
