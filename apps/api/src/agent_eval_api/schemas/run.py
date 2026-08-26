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


class RunTelemetryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    wall_clock_ms: int | None
    compute_ms: int | None
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    estimated_cost: None = None
    provider_usage_available: bool


class RunResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    status: str
    created_at: datetime
    pins: RunPinsResponse
    failure_reason: str | None
    failure_category: str | None = None
    cancellation_reason: str | None
    sandbox_id: str | None
    expected_grader_count: int
    produced_score_count: int
    is_partially_graded: bool
    scores: list[ScoreResponse]
    telemetry: RunTelemetryResponse | None = None
    execution_mode: str | None = None
    execution_metadata: dict[str, str] = Field(default_factory=dict)
    execution_group_id: str | None = None

    @classmethod
    def from_dto(cls, dto: RunDTO) -> RunResponse:
        telem = dto.telemetry
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
            failure_category=dto.failure_category,
            cancellation_reason=dto.cancellation_reason,
            sandbox_id=dto.sandbox_id,
            expected_grader_count=dto.expected_grader_count,
            produced_score_count=dto.produced_score_count,
            is_partially_graded=dto.is_partially_graded,
            scores=[ScoreResponse.from_dto(s) for s in dto.scores],
            telemetry=RunTelemetryResponse(
                wall_clock_ms=telem.wall_clock_ms,
                compute_ms=telem.compute_ms,
                input_tokens=telem.input_tokens,
                output_tokens=telem.output_tokens,
                total_tokens=telem.total_tokens,
                estimated_cost=None,
                provider_usage_available=telem.provider_usage_available,
            ),
            execution_mode=dto.execution_mode,
            execution_metadata=dict(dto.execution_metadata),
            execution_group_id=dto.execution_group_id,
        )


class ScoreAggregateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    passed: bool | None
    overall_score: float | None
    objective_failed: bool
    score_count: int
    reason: str


class ReproducibilityResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    can_reproduce: bool
    missing: list[str]
    notes: str


class RunProvenanceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    status: str
    created_at: datetime
    failure_reason: str | None
    failure_category: str | None = None
    cancellation_reason: str | None
    project_id: str
    case_version_id: str
    prompt_version_id: str
    agent_version_id: str
    adapter_version_id: str
    platform_version_id: str
    grader_version_ids: list[str]
    suite_version_id: str | None
    repository_url: str | None
    commit_sha: str | None
    subdirectory: str | None
    agent_name: str | None
    agent_version_label: str | None
    adapter_name: str | None
    adapter_version_label: str | None
    adapter_key: str | None
    platform_name: str | None = None
    platform_version_label: str | None = None
    platform_policy_summaries: dict[str, dict[str, str]] = Field(default_factory=dict)
    grader_summaries: list[dict[str, Any]]
    score_aggregate: ScoreAggregateResponse
    expected_grader_count: int
    produced_score_count: int
    is_partially_graded: bool
    telemetry: RunTelemetryResponse
    event_count: int
    artifact_count: int
    execution_mode: str | None = None
    execution_metadata: dict[str, str] = Field(default_factory=dict)
    benchmark_key: str | None = None
    suite_version_id_as_benchmark: str | None = None
    reproducibility: ReproducibilityResponse


class CompareRunsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_ids: list[str] = Field(min_length=2, max_length=5)


class RunComparisonEntryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    status: str
    failure_reason: str | None
    failure_category: str | None = None
    pins: RunPinsResponse
    repository_url: str | None
    commit_sha: str | None
    adapter_key: str | None
    adapter_name: str | None
    prompt_version: str | None
    agent_version: str | None
    telemetry: RunTelemetryResponse
    score_aggregate: ScoreAggregateResponse
    duration_ms: int | None
    execution_mode: str | None = None
    benchmark_key: str | None = None
    suite_version_id: str | None = None


class RunComparisonDeltaResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    score_delta: float | None
    pass_changed: bool | None
    duration_delta_ms: int | None
    pin_differences: list[str]


class RunComparabilityResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    compatible: bool
    shared_dimensions: list[str]
    agent_difference_dimensions: list[str]
    mismatches: list[str]
    expected_agent_differences: list[str]
    benchmark_key: str | None
    notes: str


class RunComparisonResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    baseline_run_id: str
    runs: list[RunComparisonEntryResponse]
    deltas: list[RunComparisonDeltaResponse]
    comparability: RunComparabilityResponse


class BenchmarkMatrixCellResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    adapter_key: str | None
    adapter_name: str | None
    execution_mode: str | None
    run_id: str
    status: str
    overall_score: float | None
    passed: bool | None
    duration_ms: int | None
    failure_category: str | None


class BenchmarkMatrixResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    benchmark_key: str | None
    comparable: bool
    notes: str
    cells: list[BenchmarkMatrixCellResponse]
    mismatches: list[str]


class FailingGraderReasonResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    grader_id: str
    grader_version_id: str
    reason: str


class RunDiagnosisResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    status: str
    summary: str
    category: str | None = None
    reason: str | None
    evidence: list[str]
    failing_grader_reasons: list[FailingGraderReasonResponse]
    last_events: list[ExecutionEventResponse]
    relevant_artifact_ids: list[str]


class ArtifactPreviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_id: str
    content_type: str
    size_bytes: int
    preview: str | None
    truncated: bool
    previewable: bool
