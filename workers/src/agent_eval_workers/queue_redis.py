"""Adapt Infrastructure ``RedisRunQueue`` to Workers ``WorkerQueuePort``."""

from __future__ import annotations

from dataclasses import dataclass

from agent_eval_infrastructure.queue.redis_run_queue import RedisRunQueue

from agent_eval_workers.worker.queue import ClaimedTask


@dataclass(slots=True)
class RedisWorkerQueue:
    """Worker-facing claim/ack/release over Infrastructure Redis run queue."""

    queue: RedisRunQueue

    def claim(self, *, block: bool = True) -> ClaimedTask | None:
        claimed = self.queue.claim_run(block=block)
        if claimed is None:
            return None
        return ClaimedTask(run_id=claimed.run_id, receipt=claimed.run_id.value)

    def ack(self, task: ClaimedTask) -> None:
        self.queue.acknowledge_run(task.run_id)

    def release(self, task: ClaimedTask) -> None:
        self.queue.release_run(task.run_id)

    def heartbeat(self, task: ClaimedTask) -> None:
        del task  # Redis list lease is visibility via processing list membership.

    def extend_visibility(self, task: ClaimedTask, *, seconds: float) -> None:
        del task, seconds
