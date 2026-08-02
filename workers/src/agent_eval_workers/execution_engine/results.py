"""Execution Engine results reported to the Worker (orchestration outcomes)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from agent_eval_workers.lifecycle.phases import OrchestrationPhase
from agent_eval_workers.lifecycle.triggers import FailureCause


class EngineOutcomeKind(StrEnum):
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"
    """Lifecycle reached Failed — Worker acknowledges (retry already decided)."""

    RECOVERABLE_FAILURE = "recoverable_failure"
    """Classified failure; Worker owns whether to release or finalize."""

    INTERRUPTED = "interrupted"
    """Worker shutdown / crash path — release for redelivery."""

    ALREADY_TERMINAL = "already_terminal"
    """Redelivered task for a Run that is already closed."""


@dataclass(frozen=True, slots=True)
class EngineResult:
    """What the Execution Engine reports after hosting one Run's orchestration."""

    kind: EngineOutcomeKind
    phase: OrchestrationPhase
    failure_cause: FailureCause | None = None
    resume_phase: OrchestrationPhase | None = None
    """Last durable phase before a recoverable failure or interruption."""
