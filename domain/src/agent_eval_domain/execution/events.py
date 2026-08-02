"""Run lifecycle domain events (Domain Model §11)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agent_eval_domain.common.events import DomainEvent
from agent_eval_domain.common.ids import (
    ArtifactId,
    ExecutionEventId,
    GraderVersionId,
    RunId,
    ScoreId,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class RunCreated(DomainEvent):
    run_id: RunId
    project_id: str
    case_version_id: str
    prompt_version_id: str
    agent_version_id: str
    adapter_version_id: str
    suite_version_id: str | None
    platform_version_id: str
    grader_version_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base.update(
            {
                "run_id": self.run_id.value,
                "project_id": self.project_id,
                "case_version_id": self.case_version_id,
                "prompt_version_id": self.prompt_version_id,
                "agent_version_id": self.agent_version_id,
                "adapter_version_id": self.adapter_version_id,
                "suite_version_id": self.suite_version_id,
                "platform_version_id": self.platform_version_id,
                "grader_version_ids": list(self.grader_version_ids),
            }
        )
        return base


@dataclass(frozen=True, slots=True, kw_only=True)
class RunQueued(DomainEvent):
    run_id: RunId


@dataclass(frozen=True, slots=True, kw_only=True)
class RunStarted(DomainEvent):
    run_id: RunId
    sandbox_id: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionEventRecorded(DomainEvent):
    run_id: RunId
    execution_event_id: ExecutionEventId
    sequence: int


@dataclass(frozen=True, slots=True, kw_only=True)
class ArtifactStored(DomainEvent):
    run_id: RunId
    artifact_id: ArtifactId


@dataclass(frozen=True, slots=True, kw_only=True)
class RunGradingStarted(DomainEvent):
    run_id: RunId


@dataclass(frozen=True, slots=True, kw_only=True)
class ScoreProduced(DomainEvent):
    run_id: RunId
    score_id: ScoreId
    grader_version_id: GraderVersionId


@dataclass(frozen=True, slots=True, kw_only=True)
class RunCompleted(DomainEvent):
    run_id: RunId
    expected_grader_count: int
    produced_score_count: int
    is_partially_graded: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class RunFailed(DomainEvent):
    run_id: RunId
    reason: str


@dataclass(frozen=True, slots=True, kw_only=True)
class RunCancelled(DomainEvent):
    run_id: RunId
    reason: str | None = None
