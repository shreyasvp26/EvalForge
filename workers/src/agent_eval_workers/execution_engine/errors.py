"""Recoverable execution errors reported by Engine step hooks / ports."""

from __future__ import annotations

from agent_eval_workers.lifecycle.triggers import FailureCause


class RecoverableExecutionError(Exception):
    """Infrastructure-classified failure the Worker may retry.

    Raised from Engine step hooks (or future port adapters). Does not itself
    mutate Run lifecycle — the Engine reports and the Worker decides.
    """

    def __init__(self, message: str, *, cause: FailureCause) -> None:
        super().__init__(message)
        self.cause = cause
