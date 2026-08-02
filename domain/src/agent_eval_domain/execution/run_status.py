"""Evaluation Run status machine (Domain Model §7)."""

from __future__ import annotations

from enum import StrEnum

from agent_eval_domain.common.errors import InvalidStateTransition


class RunStatus(StrEnum):
    CREATED = "created"
    QUEUED = "queued"
    RUNNING = "running"
    GRADING = "grading"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


TERMINAL_STATUSES: frozenset[RunStatus] = frozenset(
    {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED}
)

_RUN_TRANSITIONS: dict[RunStatus, frozenset[RunStatus]] = {
    RunStatus.CREATED: frozenset({RunStatus.QUEUED}),
    RunStatus.QUEUED: frozenset({RunStatus.RUNNING, RunStatus.CANCELLED}),
    RunStatus.RUNNING: frozenset(
        {RunStatus.GRADING, RunStatus.FAILED, RunStatus.CANCELLED}
    ),
    RunStatus.GRADING: frozenset({RunStatus.COMPLETED, RunStatus.FAILED}),
    RunStatus.COMPLETED: frozenset(),
    RunStatus.FAILED: frozenset(),
    RunStatus.CANCELLED: frozenset(),
}


def assert_run_transition(*, current: RunStatus, target: RunStatus) -> None:
    allowed = _RUN_TRANSITIONS[current]
    if target not in allowed:
        raise InvalidStateTransition(
            f"Run cannot transition from {current} to {target}",
            from_state=current.value,
            to_state=target.value,
            entity="EvaluationRun",
        )


def is_terminal(status: RunStatus) -> bool:
    return status in TERMINAL_STATUSES
