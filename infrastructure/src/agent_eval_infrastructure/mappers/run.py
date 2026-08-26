"""Run / Execution Event / Artifact / Score ORM ↔ Domain mapping."""

from __future__ import annotations

from typing import Any

from agent_eval_domain.common.ids import (
    AdapterVersionId,
    AgentVersionId,
    ArtifactId,
    CaseVersionId,
    ExecutionEventId,
    GraderId,
    GraderVersionId,
    PlatformVersionId,
    ProjectId,
    PromptVersionId,
    RunId,
    ScoreId,
    SuiteVersionId,
)
from agent_eval_domain.execution.configuration import (
    ExecutionMode,
    sanitize_execution_metadata,
)
from agent_eval_domain.execution.entities import (
    Artifact,
    ArtifactKind,
    ExecutionCost,
    ExecutionEvent,
    Score,
    ScoreValue,
)
from agent_eval_domain.execution.failure import FailureCategory
from agent_eval_domain.execution.normalized_model import action_kind_of
from agent_eval_domain.execution.run import EvaluationRun, RunPins
from agent_eval_domain.execution.run_status import RunStatus

from agent_eval_infrastructure.database.models.execution.artifact import ArtifactOrm
from agent_eval_infrastructure.database.models.execution.event import ExecutionEventOrm
from agent_eval_infrastructure.database.models.execution.run import RunOrm
from agent_eval_infrastructure.database.models.execution.score import ScoreOrm
from agent_eval_infrastructure.mappers.ndm import action_from_payload, action_to_payload


def score_to_domain(row: ScoreOrm) -> Score:
    return Score(
        id=ScoreId(row.id),
        run_id=RunId(row.run_id),
        grader_id=GraderId(row.grader_id),
        grader_version_id=GraderVersionId(row.grader_version_id),
        value=ScoreValue(
            numeric=row.numeric_value,
            categorical=row.categorical_value,
            passed=row.passed,
            detail=dict(row.detail or {}),
        ),
        created_at=row.created_at,
        explanation_artifact_id=(
            ArtifactId(row.explanation_artifact_id)
            if row.explanation_artifact_id
            else None
        ),
    )


def artifact_to_domain(row: ArtifactOrm) -> Artifact:
    return Artifact(
        id=ArtifactId(row.id),
        run_id=RunId(row.run_id),
        kind=ArtifactKind(row.kind),
        storage_key=row.storage_key,
        content_type=row.content_type,
        size_bytes=row.size_bytes,
        checksum=row.checksum,
        created_at=row.created_at,
        produced_by_grader_version_id=(
            GraderVersionId(row.produced_by_grader_version_id)
            if row.produced_by_grader_version_id
            else None
        ),
    )


def execution_event_to_domain(row: ExecutionEventOrm) -> ExecutionEvent:
    action = action_from_payload(dict(row.action_payload or {}))
    metadata_raw: dict[str, Any] = dict(row.event_metadata or {})
    return ExecutionEvent(
        id=ExecutionEventId(row.id),
        run_id=RunId(row.run_id),
        sequence=row.sequence,
        kind=action_kind_of(action),
        action=action,
        occurred_at=row.occurred_at,
        artifact_ids=tuple(ArtifactId(a) for a in list(row.artifact_ids or [])),
        metadata={str(k): str(v) for k, v in metadata_raw.items()},
    )


def _cost_to_domain(row: RunOrm) -> ExecutionCost | None:
    if all(
        v is None
        for v in (
            row.input_tokens,
            row.output_tokens,
            row.wall_clock_ms,
            row.compute_ms,
        )
    ):
        return None
    return ExecutionCost(
        input_tokens=row.input_tokens,
        output_tokens=row.output_tokens,
        wall_clock_ms=row.wall_clock_ms or 0,
        compute_ms=row.compute_ms or 0,
    )


def run_to_domain(
    row: RunOrm,
    events: list[ExecutionEventOrm],
    artifacts: list[ArtifactOrm],
    scores: list[ScoreOrm],
) -> EvaluationRun:
    pins = RunPins(
        project_id=ProjectId(row.project_id),
        case_version_id=CaseVersionId(row.case_version_id),
        prompt_version_id=PromptVersionId(row.prompt_version_id),
        agent_version_id=AgentVersionId(row.agent_version_id),
        adapter_version_id=AdapterVersionId(row.adapter_version_id),
        platform_version_id=PlatformVersionId(row.platform_version_id),
        grader_version_ids=tuple(
            GraderVersionId(g) for g in list(row.grader_version_ids or [])
        ),
        suite_version_id=(
            SuiteVersionId(row.suite_version_id) if row.suite_version_id else None
        ),
    )
    mapped_events = [
        execution_event_to_domain(e)
        for e in sorted(events, key=lambda item: item.sequence)
    ]
    mapped_artifacts = [artifact_to_domain(a) for a in artifacts]
    mapped_scores = [score_to_domain(s) for s in scores]
    next_sequence = (
        max((e.sequence for e in mapped_events), default=-1) + 1 if mapped_events else 0
    )
    return EvaluationRun(
        id=RunId(row.id),
        pins=pins,
        status=RunStatus(row.status),
        created_at=row.created_at,
        cost=_cost_to_domain(row),
        failure_reason=row.failure_reason,
        failure_category=(
            FailureCategory(row.failure_category) if row.failure_category else None
        ),
        cancellation_reason=row.cancellation_reason,
        execution_mode=(
            ExecutionMode(row.execution_mode) if row.execution_mode else None
        ),
        execution_metadata=sanitize_execution_metadata(
            {str(k): str(v) for k, v in dict(row.execution_metadata or {}).items()}
        ),
        execution_group_id=getattr(row, "execution_group_id", None),
        sandbox=None,
        _execution_events=mapped_events,
        _artifacts=mapped_artifacts,
        _scores=mapped_scores,
        _next_sequence=next_sequence,
    )


def apply_run_to_orm(run: EvaluationRun, row: RunOrm) -> None:
    """Map mutable Run fields onto an existing or new ORM row.

    Pins are written only when the row is new (callers set them on insert).
    ``lock_version`` is owned by SQLAlchemy optimistic concurrency — do not set.
    """
    row.status = run.status.value
    row.failure_reason = run.failure_reason
    row.failure_category = (
        run.failure_category.value if run.failure_category is not None else None
    )
    row.cancellation_reason = run.cancellation_reason
    row.execution_mode = (
        run.execution_mode.value if run.execution_mode is not None else None
    )
    row.execution_metadata = sanitize_execution_metadata(dict(run.execution_metadata))
    if run.cost is not None:
        row.input_tokens = run.cost.input_tokens
        row.output_tokens = run.cost.output_tokens
        row.wall_clock_ms = run.cost.wall_clock_ms
        row.compute_ms = run.cost.compute_ms


def new_run_orm(run: EvaluationRun) -> RunOrm:
    row = RunOrm(
        id=run.id.value,
        project_id=run.pins.project_id.value,
        case_version_id=run.pins.case_version_id.value,
        prompt_version_id=run.pins.prompt_version_id.value,
        agent_version_id=run.pins.agent_version_id.value,
        adapter_version_id=run.pins.adapter_version_id.value,
        platform_version_id=run.pins.platform_version_id.value,
        suite_version_id=(
            run.pins.suite_version_id.value if run.pins.suite_version_id else None
        ),
        grader_version_ids=[g.value for g in run.pins.grader_version_ids],
        execution_group_id=run.execution_group_id,
        created_at=run.created_at,
    )
    apply_run_to_orm(run, row)
    return row


def execution_event_to_orm(event: ExecutionEvent) -> ExecutionEventOrm:
    return ExecutionEventOrm(
        id=event.id.value,
        run_id=event.run_id.value,
        sequence=event.sequence,
        kind=event.kind.value,
        action_payload=action_to_payload(event.action),
        occurred_at=event.occurred_at,
        event_metadata=dict(event.metadata),
        artifact_ids=[a.value for a in event.artifact_ids],
    )


def artifact_to_orm(artifact: Artifact) -> ArtifactOrm:
    return ArtifactOrm(
        id=artifact.id.value,
        run_id=artifact.run_id.value,
        kind=artifact.kind.value,
        storage_key=artifact.storage_key,
        content_type=artifact.content_type,
        size_bytes=artifact.size_bytes,
        checksum=artifact.checksum,
        created_at=artifact.created_at,
        produced_by_grader_version_id=(
            artifact.produced_by_grader_version_id.value
            if artifact.produced_by_grader_version_id
            else None
        ),
    )


def score_to_orm(score: Score) -> ScoreOrm:
    return ScoreOrm(
        id=score.id.value,
        run_id=score.run_id.value,
        grader_id=score.grader_id.value,
        grader_version_id=score.grader_version_id.value,
        numeric_value=score.value.numeric,
        categorical_value=score.value.categorical,
        passed=score.value.passed,
        detail=dict(score.value.detail),
        created_at=score.created_at,
        explanation_artifact_id=(
            score.explanation_artifact_id.value
            if score.explanation_artifact_id
            else None
        ),
    )
