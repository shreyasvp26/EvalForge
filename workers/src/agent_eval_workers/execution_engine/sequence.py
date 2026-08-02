"""Happy-path trigger sequence helpers for resumable orchestration."""

from __future__ import annotations

from agent_eval_workers.lifecycle.phases import OrchestrationPhase
from agent_eval_workers.lifecycle.triggers import LifecycleTrigger

# Ordered happy-path edges: applying each trigger advances to the next phase.
_HAPPY_PATH: tuple[tuple[OrchestrationPhase, LifecycleTrigger], ...] = (
    (OrchestrationPhase.QUEUED, LifecycleTrigger.CLAIM),
    (OrchestrationPhase.CLAIMED, LifecycleTrigger.BEGIN_SANDBOX_PROVISIONING),
    (
        OrchestrationPhase.SANDBOX_PROVISIONING,
        LifecycleTrigger.SANDBOX_READY,
    ),
    (OrchestrationPhase.SANDBOX_READY, LifecycleTrigger.START_ADAPTER),
    (OrchestrationPhase.ADAPTER_STARTING, LifecycleTrigger.ADAPTER_STARTED),
    (OrchestrationPhase.EXECUTION_STREAMING, LifecycleTrigger.ADAPTER_FINISHED),
    (OrchestrationPhase.ADAPTER_FINISHED, LifecycleTrigger.PERSIST_FINAL_EVENTS),
    (
        OrchestrationPhase.FINAL_EVENT_PERSISTENCE,
        LifecycleTrigger.FINALS_PERSISTED,
    ),
    (OrchestrationPhase.GRADING_SCHEDULED, LifecycleTrigger.GRADING_FINISHED),
)


def next_happy_path_trigger(phase: OrchestrationPhase) -> LifecycleTrigger | None:
    """Return the next happy-path trigger for ``phase``, or ``None`` if none."""
    for from_phase, trigger in _HAPPY_PATH:
        if from_phase is phase:
            return trigger
    return None


def happy_path_triggers_from(phase: OrchestrationPhase) -> tuple[LifecycleTrigger, ...]:
    """Remaining happy-path triggers starting at ``phase`` (inclusive)."""
    started = False
    triggers: list[LifecycleTrigger] = []
    for from_phase, trigger in _HAPPY_PATH:
        if from_phase is phase:
            started = True
        if started:
            triggers.append(trigger)
    return tuple(triggers)
