"""Worker-owned retry policy (Execution Engine Architecture — Retry Philosophy).

The Execution Engine reports classified failures. The Worker decides whether
to release for redelivery or acknowledge a terminal outcome.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from agent_eval_workers.lifecycle.triggers import FailureCause


class RetryAction(StrEnum):
    """What the Worker should do with the queue lease after an Engine report."""

    ACK = "ack"
    """Remove from the queue — Run reached a definitive outcome."""

    RELEASE = "release"
    """Return for redelivery — retryable / interrupted work."""


# Infrastructure / transient causes that are safe to retry (System Overview).
_RETRYABLE_CAUSES: frozenset[FailureCause] = frozenset(
    {
        FailureCause.SANDBOX_FAILURE,
        FailureCause.WORKER_FAILURE,
        FailureCause.REPOSITORY_PREPARATION,
    }
)


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Bounded retry budget for infrastructure-classified failures."""

    max_attempts: int = 3

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            msg = "max_attempts must be >= 1"
            raise ValueError(msg)

    def is_retryable(self, cause: FailureCause) -> bool:
        return cause in _RETRYABLE_CAUSES

    def should_retry(self, cause: FailureCause, *, attempt: int) -> bool:
        """Return True when the Worker should release for another attempt."""
        if attempt < 1:
            msg = "attempt must be >= 1"
            raise ValueError(msg)
        return self.is_retryable(cause) and attempt < self.max_attempts

    def action_for_failure(self, cause: FailureCause, *, attempt: int) -> RetryAction:
        if self.should_retry(cause, attempt=attempt):
            return RetryAction.RELEASE
        return RetryAction.ACK
