"""In-memory RunQueue for deterministic unit tests (same semantics as Redis)."""

from __future__ import annotations

from collections import deque

from agent_eval_domain.common.ids import RunId

from agent_eval_infrastructure.queue.redis_run_queue import ClaimedRun


class InMemoryRunQueue:
    """Process-local queue implementing Application ``RunQueue`` + claim/ack."""

    def __init__(self) -> None:
        self._pending: deque[str] = deque()
        self._processing: deque[str] = deque()

    def enqueue_run(self, run_id: RunId) -> None:
        self._pending.append(run_id.value)

    def claim_run(self, *, block: bool = True) -> ClaimedRun | None:
        del block  # non-blocking in-memory; Workers supply real Redis blocking
        if not self._pending:
            return None
        value = self._pending.popleft()
        self._processing.append(value)
        return ClaimedRun(run_id=RunId(value))

    def acknowledge_run(self, run_id: RunId) -> None:
        try:
            self._processing.remove(run_id.value)
        except ValueError:
            return

    def release_run(self, run_id: RunId) -> None:
        try:
            self._processing.remove(run_id.value)
        except ValueError:
            return
        self._pending.append(run_id.value)

    def pending_run_ids(self) -> list[RunId]:
        return [RunId(v) for v in self._pending]
