"""Event pipeline errors — persistence failures reported to the Worker."""

from __future__ import annotations

from agent_eval_shared.errors import AppError


class PersistenceFailure(AppError):
    """Durable recording failed; Worker owns retry policy.

    Raised so partial history is never left ambiguously mid-batch: the pipeline
    stops at the first failed item and does not continue flushing.
    """

    def __init__(
        self,
        message: str,
        *,
        run_id: str,
        code: str = "EVENT_PERSISTENCE_FAILED",
        retryable: bool = True,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(
            message,
            code=code,
            details={"run_id": run_id},
            retryable=retryable,
            cause=cause,
        )
        self.run_id = run_id
