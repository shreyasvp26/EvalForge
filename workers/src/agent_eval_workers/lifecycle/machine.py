"""Deterministic Run lifecycle state machine."""

from __future__ import annotations

from dataclasses import dataclass, field

from agent_eval_domain.common.ids import RunId
from agent_eval_domain.execution.run_status import RunStatus

from agent_eval_workers.lifecycle.domain_mapping import domain_status_for
from agent_eval_workers.lifecycle.errors import IllegalLifecycleTransition
from agent_eval_workers.lifecycle.phases import (
    OrchestrationPhase,
    is_terminal_phase,
)
from agent_eval_workers.lifecycle.transitions import (
    LifecycleTransition,
    _UnresolvedTransition,
    allowed_triggers,
    resolve_transition,
)
from agent_eval_workers.lifecycle.triggers import FailureCause, LifecycleTrigger


@dataclass(slots=True)
class RunLifecycle:
    """Explicit orchestration state for one Run.

    Owns sequencing and transition validation only. Does not execute Adapters,
    grade, persist, or enqueue.
    """

    run_id: RunId
    phase: OrchestrationPhase = OrchestrationPhase.QUEUED
    failure_cause: FailureCause | None = None
    history: list[LifecycleTransition] = field(default_factory=list)

    @property
    def domain_status(self) -> RunStatus:
        return domain_status_for(self.phase)

    @property
    def is_terminal(self) -> bool:
        return is_terminal_phase(self.phase)

    def allowed_triggers(self) -> frozenset[LifecycleTrigger]:
        return allowed_triggers(self.phase)

    def apply(self, trigger: LifecycleTrigger) -> LifecycleTransition:
        """Apply a validated transition or raise ``IllegalLifecycleTransition``."""
        if self.is_terminal:
            raise IllegalLifecycleTransition(
                f"Run {self.run_id.value} is terminal ({self.phase.value}); "
                f"cannot apply {trigger.value}",
                from_phase=self.phase.value,
                trigger=trigger.value,
            )
        try:
            transition = resolve_transition(self.phase, trigger)
        except _UnresolvedTransition as exc:
            raise IllegalLifecycleTransition(
                f"Illegal lifecycle transition for run {self.run_id.value}: "
                f"{self.phase.value} + {trigger.value}",
                from_phase=self.phase.value,
                trigger=trigger.value,
            ) from exc

        self.phase = transition.to_phase
        self.failure_cause = transition.failure_cause
        self.history.append(transition)
        return transition
