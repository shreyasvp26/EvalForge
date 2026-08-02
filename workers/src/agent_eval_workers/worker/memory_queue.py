"""In-memory WorkerQueuePort for deterministic Worker tests."""

from __future__ import annotations

from collections import deque

from agent_eval_domain.common.ids import RunId

from agent_eval_workers.worker.queue import ClaimedTask


class InMemoryWorkerQueue:
    """Process-local claim / ack / release / heartbeat queue."""

    def __init__(self) -> None:
        self._pending: deque[str] = deque()
        self._processing: dict[str, ClaimedTask] = {}
        self.heartbeats: list[RunId] = []
        self.visibility_extensions: list[tuple[RunId, float]] = []
        self.acked: list[RunId] = []
        self.released: list[RunId] = []

    def enqueue(self, run_id: RunId) -> None:
        self._pending.append(run_id.value)

    def claim(self, *, block: bool = True) -> ClaimedTask | None:
        del block
        if not self._pending:
            return None
        value = self._pending.popleft()
        task = ClaimedTask(run_id=RunId(value), receipt=f"rcpt-{value}")
        self._processing[value] = task
        return task

    def ack(self, task: ClaimedTask) -> None:
        self._processing.pop(task.run_id.value, None)
        self.acked.append(task.run_id)

    def release(self, task: ClaimedTask) -> None:
        self._processing.pop(task.run_id.value, None)
        self._pending.append(task.run_id.value)
        self.released.append(task.run_id)

    def heartbeat(self, task: ClaimedTask) -> None:
        self.heartbeats.append(task.run_id)

    def extend_visibility(self, task: ClaimedTask, *, seconds: float) -> None:
        self.visibility_extensions.append((task.run_id, seconds))

    def pending_ids(self) -> list[RunId]:
        return [RunId(v) for v in self._pending]
