"""Explicit transition table for Run lifecycle orchestration.

Every legal edge is named. Anything absent from this table is illegal and
fails immediately when applied.
"""

from __future__ import annotations

from dataclasses import dataclass

from agent_eval_workers.lifecycle.phases import OrchestrationPhase
from agent_eval_workers.lifecycle.triggers import FailureCause, LifecycleTrigger

# Happy-path edges: (from_phase, trigger) → to_phase
_HAPPY_PATH: dict[tuple[OrchestrationPhase, LifecycleTrigger], OrchestrationPhase] = {
    (OrchestrationPhase.QUEUED, LifecycleTrigger.CLAIM): OrchestrationPhase.CLAIMED,
    (
        OrchestrationPhase.CLAIMED,
        LifecycleTrigger.BEGIN_SANDBOX_PROVISIONING,
    ): OrchestrationPhase.SANDBOX_PROVISIONING,
    (
        OrchestrationPhase.SANDBOX_PROVISIONING,
        LifecycleTrigger.SANDBOX_READY,
    ): OrchestrationPhase.SANDBOX_READY,
    (
        OrchestrationPhase.SANDBOX_READY,
        LifecycleTrigger.START_ADAPTER,
    ): OrchestrationPhase.ADAPTER_STARTING,
    (
        OrchestrationPhase.ADAPTER_STARTING,
        LifecycleTrigger.ADAPTER_STARTED,
    ): OrchestrationPhase.EXECUTION_STREAMING,
    (
        OrchestrationPhase.EXECUTION_STREAMING,
        LifecycleTrigger.ADAPTER_FINISHED,
    ): OrchestrationPhase.ADAPTER_FINISHED,
    (
        OrchestrationPhase.ADAPTER_FINISHED,
        LifecycleTrigger.PERSIST_FINAL_EVENTS,
    ): OrchestrationPhase.FINAL_EVENT_PERSISTENCE,
    (
        OrchestrationPhase.FINAL_EVENT_PERSISTENCE,
        LifecycleTrigger.FINALS_PERSISTED,
    ): OrchestrationPhase.GRADING_SCHEDULED,
    (
        OrchestrationPhase.GRADING_SCHEDULED,
        LifecycleTrigger.GRADING_FINISHED,
    ): OrchestrationPhase.COMPLETED,
}

_CANCELLABLE: frozenset[OrchestrationPhase] = frozenset(
    {
        OrchestrationPhase.QUEUED,
        OrchestrationPhase.CLAIMED,
        OrchestrationPhase.SANDBOX_PROVISIONING,
        OrchestrationPhase.SANDBOX_READY,
        OrchestrationPhase.ADAPTER_STARTING,
        OrchestrationPhase.EXECUTION_STREAMING,
        OrchestrationPhase.ADAPTER_FINISHED,
        OrchestrationPhase.FINAL_EVENT_PERSISTENCE,
        OrchestrationPhase.GRADING_SCHEDULED,
    }
)

_FAILABLE: frozenset[OrchestrationPhase] = frozenset(
    {
        OrchestrationPhase.CLAIMED,
        OrchestrationPhase.SANDBOX_PROVISIONING,
        OrchestrationPhase.SANDBOX_READY,
        OrchestrationPhase.ADAPTER_STARTING,
        OrchestrationPhase.EXECUTION_STREAMING,
        OrchestrationPhase.ADAPTER_FINISHED,
        OrchestrationPhase.FINAL_EVENT_PERSISTENCE,
        OrchestrationPhase.GRADING_SCHEDULED,
    }
)

_FAILURE_TRIGGER_TO_CAUSE: dict[LifecycleTrigger, FailureCause] = {
    LifecycleTrigger.ADAPTER_FAILED: FailureCause.ADAPTER_FAILURE,
    LifecycleTrigger.SANDBOX_FAILED: FailureCause.SANDBOX_FAILURE,
    LifecycleTrigger.WORKER_FAILED: FailureCause.WORKER_FAILURE,
    LifecycleTrigger.TIMEOUT: FailureCause.TIMEOUT,
    LifecycleTrigger.RESOURCE_EXHAUSTED: FailureCause.RESOURCE_EXHAUSTION,
}

_FAILURE_PHASES: dict[LifecycleTrigger, frozenset[OrchestrationPhase]] = {
    LifecycleTrigger.ADAPTER_FAILED: frozenset(
        {
            OrchestrationPhase.ADAPTER_STARTING,
            OrchestrationPhase.EXECUTION_STREAMING,
            OrchestrationPhase.ADAPTER_FINISHED,
        }
    ),
    LifecycleTrigger.SANDBOX_FAILED: frozenset(
        {
            OrchestrationPhase.SANDBOX_PROVISIONING,
            OrchestrationPhase.SANDBOX_READY,
            OrchestrationPhase.ADAPTER_STARTING,
            OrchestrationPhase.EXECUTION_STREAMING,
        }
    ),
    LifecycleTrigger.TIMEOUT: frozenset(
        {
            OrchestrationPhase.SANDBOX_PROVISIONING,
            OrchestrationPhase.ADAPTER_STARTING,
            OrchestrationPhase.EXECUTION_STREAMING,
        }
    ),
    LifecycleTrigger.RESOURCE_EXHAUSTED: frozenset(
        {
            OrchestrationPhase.SANDBOX_PROVISIONING,
            OrchestrationPhase.EXECUTION_STREAMING,
        }
    ),
    LifecycleTrigger.WORKER_FAILED: _FAILABLE,
}


@dataclass(frozen=True, slots=True)
class LifecycleTransition:
    """One validated step in the orchestration history."""

    from_phase: OrchestrationPhase
    to_phase: OrchestrationPhase
    trigger: LifecycleTrigger
    failure_cause: FailureCause | None = None


class _UnresolvedTransition(Exception):
    """Internal sentinel — converted to IllegalLifecycleTransition by the machine."""


def resolve_transition(
    current: OrchestrationPhase,
    trigger: LifecycleTrigger,
) -> LifecycleTransition:
    """Resolve ``(current, trigger)`` to a validated transition."""
    happy = _HAPPY_PATH.get((current, trigger))
    if happy is not None:
        return LifecycleTransition(
            from_phase=current,
            to_phase=happy,
            trigger=trigger,
        )

    if trigger is LifecycleTrigger.CANCEL and current in _CANCELLABLE:
        return LifecycleTransition(
            from_phase=current,
            to_phase=OrchestrationPhase.CANCELLED,
            trigger=trigger,
        )

    cause = _FAILURE_TRIGGER_TO_CAUSE.get(trigger)
    if cause is not None:
        allowed_phases = _FAILURE_PHASES.get(trigger, frozenset())
        if current in allowed_phases:
            return LifecycleTransition(
                from_phase=current,
                to_phase=OrchestrationPhase.FAILED,
                trigger=trigger,
                failure_cause=cause,
            )

    raise _UnresolvedTransition


def allowed_triggers(current: OrchestrationPhase) -> frozenset[LifecycleTrigger]:
    """Return every trigger that is currently legal (for tests / introspection)."""
    allowed: set[LifecycleTrigger] = set()
    for phase, trigger in _HAPPY_PATH:
        if phase is current:
            allowed.add(trigger)
    if current in _CANCELLABLE:
        allowed.add(LifecycleTrigger.CANCEL)
    for trigger in _FAILURE_TRIGGER_TO_CAUSE:
        try:
            resolve_transition(current, trigger)
            allowed.add(trigger)
        except _UnresolvedTransition:
            continue
    return frozenset(allowed)
