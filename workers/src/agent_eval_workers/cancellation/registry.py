"""In-memory cancellation registry for tests and local orchestration."""

from __future__ import annotations

from agent_eval_domain.common.ids import RunId


class InMemoryCancellationRegistry:
    """Tracks cancel requests without Infrastructure coupling."""

    def __init__(self) -> None:
        self._requested: set[str] = set()

    def request_cancel(self, run_id: RunId) -> None:
        self._requested.add(run_id.value)

    def clear(self, run_id: RunId) -> None:
        self._requested.discard(run_id.value)

    def is_cancel_requested(self, run_id: RunId) -> bool:
        return run_id.value in self._requested
