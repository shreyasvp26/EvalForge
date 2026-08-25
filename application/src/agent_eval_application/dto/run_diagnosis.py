"""Run failure diagnosis DTOs."""

from __future__ import annotations

from dataclasses import dataclass

from agent_eval_application.dto.run import ExecutionEventDTO


@dataclass(frozen=True, slots=True)
class FailingGraderReasonDTO:
    grader_id: str
    grader_version_id: str
    reason: str


@dataclass(frozen=True, slots=True)
class RunDiagnosisDTO:
    run_id: str
    status: str
    summary: str
    category: str | None
    reason: str | None
    evidence: tuple[str, ...]
    failing_grader_reasons: tuple[FailingGraderReasonDTO, ...]
    last_events: tuple[ExecutionEventDTO, ...]
    relevant_artifact_ids: tuple[str, ...]
