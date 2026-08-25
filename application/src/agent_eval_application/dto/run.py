"""Run DTOs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from agent_eval_domain.execution.run import EvaluationRun


@dataclass(frozen=True, slots=True)
class RunPinsDTO:
    project_id: str
    case_version_id: str
    prompt_version_id: str
    agent_version_id: str
    adapter_version_id: str
    platform_version_id: str
    grader_version_ids: tuple[str, ...]
    suite_version_id: str | None


@dataclass(frozen=True, slots=True)
class ScoreValueDTO:
    numeric: float | None
    categorical: str | None
    passed: bool | None
    detail: dict[str, object]


@dataclass(frozen=True, slots=True)
class ScoreDTO:
    id: str
    grader_id: str
    grader_version_id: str
    value: ScoreValueDTO
    explanation_artifact_id: str | None


@dataclass(frozen=True, slots=True)
class RunDTO:
    id: str
    status: str
    created_at: datetime
    pins: RunPinsDTO
    failure_reason: str | None
    failure_category: str | None
    cancellation_reason: str | None
    sandbox_id: str | None
    expected_grader_count: int
    produced_score_count: int
    is_partially_graded: bool
    scores: tuple[ScoreDTO, ...]

    @classmethod
    def from_domain(cls, run: EvaluationRun) -> RunDTO:
        pins = run.pins
        return cls(
            id=run.id.value,
            status=run.status.value,
            created_at=run.created_at,
            pins=RunPinsDTO(
                project_id=pins.project_id.value,
                case_version_id=pins.case_version_id.value,
                prompt_version_id=pins.prompt_version_id.value,
                agent_version_id=pins.agent_version_id.value,
                adapter_version_id=pins.adapter_version_id.value,
                platform_version_id=pins.platform_version_id.value,
                grader_version_ids=tuple(g.value for g in pins.grader_version_ids),
                suite_version_id=(
                    pins.suite_version_id.value if pins.suite_version_id else None
                ),
            ),
            failure_reason=run.failure_reason,
            failure_category=(
                run.failure_category.value if run.failure_category is not None else None
            ),
            cancellation_reason=run.cancellation_reason,
            sandbox_id=run.sandbox.id.value if run.sandbox else None,
            expected_grader_count=run.expected_grader_count,
            produced_score_count=len(run.scores),
            is_partially_graded=run.is_partially_graded,
            scores=tuple(
                ScoreDTO(
                    id=score.id.value,
                    grader_id=score.grader_id.value,
                    grader_version_id=score.grader_version_id.value,
                    value=ScoreValueDTO(
                        numeric=score.value.numeric,
                        categorical=score.value.categorical,
                        passed=score.value.passed,
                        detail=dict(score.value.detail),
                    ),
                    explanation_artifact_id=(
                        score.explanation_artifact_id.value
                        if score.explanation_artifact_id
                        else None
                    ),
                )
                for score in run.scores
            ),
        )


@dataclass(frozen=True, slots=True)
class ExecutionEventRecordDTO:
    """Result of persisting one Execution Event (including idempotent replay)."""

    id: str
    run_id: str
    sequence: int
    kind: str
    artifact_ids: tuple[str, ...]
    occurred_at: datetime
    already_recorded: bool


@dataclass(frozen=True, slots=True)
class ArtifactRecordDTO:
    """Result of persisting one Artifact metadata row."""

    id: str
    run_id: str
    kind: str
    storage_key: str
    content_type: str
    size_bytes: int
    checksum: str
    already_recorded: bool


@dataclass(frozen=True, slots=True)
class ExecutionEventDTO:
    """Read-model Execution Event for API / query responses."""

    id: str
    run_id: str
    sequence: int
    kind: str
    action: dict[str, object]
    artifact_ids: tuple[str, ...]
    occurred_at: datetime
    metadata: dict[str, str]


@dataclass(frozen=True, slots=True)
class ArtifactDTO:
    """Read-model Artifact metadata for API / query responses."""

    id: str
    run_id: str
    kind: str
    storage_key: str
    content_type: str
    size_bytes: int
    checksum: str
    created_at: datetime
    produced_by_grader_version_id: str | None
