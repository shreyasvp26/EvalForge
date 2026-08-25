"""Diagnose why a Run failed (execution or evaluation)."""

from __future__ import annotations

from agent_eval_domain.common.ids import RunId
from agent_eval_domain.execution.entities import ArtifactKind
from agent_eval_domain.execution.ndm_codec import action_to_payload

from agent_eval_application.common.validation import require_non_empty
from agent_eval_application.dto.run import ExecutionEventDTO, RunDTO
from agent_eval_application.dto.run_diagnosis import (
    FailingGraderReasonDTO,
    RunDiagnosisDTO,
)
from agent_eval_application.ports.authorization import AuthorizationPort
from agent_eval_application.ports.unit_of_work import UnitOfWorkFactory
from agent_eval_application.queries.queries import DiagnoseRunFailureQuery
from agent_eval_application.scoring.aggregation import aggregate_scores
from agent_eval_application.use_cases.base import with_domain_errors

_RELEVANT_ARTIFACT_KINDS = {
    ArtifactKind.STDERR.value,
    ArtifactKind.LOG.value,
    "stderr",
    "log",
}


def _safe_detail_text(detail: dict[str, object]) -> str | None:
    for key in ("reason", "message", "summary", "error"):
        value = detail.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _event_summary(event: ExecutionEventDTO) -> str:
    action = event.action
    kind = str(action.get("kind", event.kind))
    if kind == "message":
        role = action.get("role", "unknown")
        content = action.get("content_summary", "")
        return f"message ({role}): {content}"
    if kind == "tool_call":
        tool = action.get("tool_name", "tool")
        return f"tool_call: {tool}"
    if kind == "tool_result":
        tool = action.get("tool_name", "tool")
        outcome = action.get("outcome_summary", "")
        return f"tool_result ({tool}): {outcome}"
    if kind == "error":
        return f"error: {action.get('message', action.get('summary', ''))}"
    return kind


class DiagnoseRunFailure:
    """Structured failure analysis without leaking secrets."""

    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        auth: AuthorizationPort,
    ) -> None:
        self._uow_factory = uow_factory
        self._auth = auth

    def execute(self, query: DiagnoseRunFailureQuery) -> RunDiagnosisDTO:
        run_id = RunId(require_non_empty(query.run_id, field="run_id"))
        with self._uow_factory() as uow:
            run = with_domain_errors(lambda: uow.runs.get(run_id))
            self._auth.ensure_can_access_project(query.actor, run.pins.project_id)
            dto = RunDTO.from_domain(run)
            aggregate = aggregate_scores(dto.scores)

            category: str | None = None
            reason = dto.failure_reason
            summary = "Run is still in progress or has no failure signal."
            evidence: list[str] = []

            if dto.status == "completed" and aggregate.passed is False:
                category = "evaluation_failure"
                reason = aggregate.reason
                summary = "Run completed but evaluation did not pass."
                evidence.append(aggregate.reason)
            elif dto.status == "failed":
                category = dto.failure_category
                summary = "Run failed during execution."
                if dto.failure_reason:
                    evidence.append(dto.failure_reason)
            elif dto.status == "cancelled":
                category = "cancelled"
                reason = dto.cancellation_reason
                summary = "Run was cancelled."
                if dto.cancellation_reason:
                    evidence.append(dto.cancellation_reason)
            elif dto.status == "completed" and aggregate.passed is True:
                summary = "Run completed and passed evaluation."
            elif aggregate.passed is None and dto.scores:
                summary = "Run finished grading but pass/fail is ambiguous."

            failing_graders: list[FailingGraderReasonDTO] = []
            for score in dto.scores:
                if score.value.passed is False:
                    detail_reason = _safe_detail_text(score.value.detail)
                    failing_graders.append(
                        FailingGraderReasonDTO(
                            grader_id=score.grader_id,
                            grader_version_id=score.grader_version_id,
                            reason=detail_reason or aggregate.reason,
                        )
                    )
                    if detail_reason:
                        evidence.append(f"grader {score.grader_id}: {detail_reason}")

            events = [
                ExecutionEventDTO(
                    id=event.id.value,
                    run_id=run.id.value,
                    sequence=event.sequence,
                    kind=event.kind.value,
                    action=action_to_payload(event.action),
                    artifact_ids=tuple(a.value for a in event.artifact_ids),
                    occurred_at=event.occurred_at,
                    metadata=dict(event.metadata),
                )
                for event in run.execution_events
            ]
            last_events = tuple(events[-5:])

            relevant_ids: list[str] = []
            for artifact in run.artifacts:
                kind = artifact.kind.value
                if kind in _RELEVANT_ARTIFACT_KINDS:
                    relevant_ids.append(artifact.id.value)

            return RunDiagnosisDTO(
                run_id=dto.id,
                status=dto.status,
                summary=summary,
                category=category,
                reason=reason,
                evidence=tuple(dict.fromkeys(evidence)),
                failing_grader_reasons=tuple(failing_graders),
                last_events=last_events,
                relevant_artifact_ids=tuple(relevant_ids),
            )
