"""Orchestration phases for a single Run (Execution Engine Architecture).

These are Engine-internal steps. Domain ``RunStatus`` remains the persisted
projection (queued / running / grading / terminal) — see ``domain_mapping``.
"""

from __future__ import annotations

from enum import StrEnum


class OrchestrationPhase(StrEnum):
    """Named steps the Execution Engine advances through for one Run."""

    QUEUED = "queued"
    CLAIMED = "claimed"
    SANDBOX_PROVISIONING = "sandbox_provisioning"
    SANDBOX_READY = "sandbox_ready"
    ADAPTER_STARTING = "adapter_starting"
    EXECUTION_STREAMING = "execution_streaming"
    ADAPTER_FINISHED = "adapter_finished"
    FINAL_EVENT_PERSISTENCE = "final_event_persistence"
    GRADING_SCHEDULED = "grading_scheduled"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


TERMINAL_PHASES: frozenset[OrchestrationPhase] = frozenset(
    {
        OrchestrationPhase.COMPLETED,
        OrchestrationPhase.FAILED,
        OrchestrationPhase.CANCELLED,
    }
)


def is_terminal_phase(phase: OrchestrationPhase) -> bool:
    return phase in TERMINAL_PHASES
