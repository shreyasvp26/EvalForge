"""Lifecycle errors — illegal transitions fail immediately."""

from __future__ import annotations

from agent_eval_shared.errors import AppError


class IllegalLifecycleTransition(AppError):
    """Raised when a trigger is not valid for the current orchestration phase."""

    def __init__(
        self,
        message: str,
        *,
        from_phase: str,
        trigger: str,
        code: str = "ILLEGAL_LIFECYCLE_TRANSITION",
    ) -> None:
        super().__init__(
            message,
            code=code,
            details={"from_phase": from_phase, "trigger": trigger},
        )
