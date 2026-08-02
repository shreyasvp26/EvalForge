"""Redis WorkerQueuePort adapter tests."""

from __future__ import annotations

from agent_eval_domain.common.ids import RunId
from agent_eval_infrastructure.queue.redis_run_queue import RedisRunQueue
from agent_eval_workers.queue_redis import RedisWorkerQueue
from agent_eval_workers.worker.queue import ClaimedTask


class FakeRedis:
    def __init__(self) -> None:
        self.lists: dict[str, list[str]] = {}

    def rpush(self, name: str, *values: str) -> int:
        self.lists.setdefault(name, []).extend(values)
        return len(self.lists[name])

    def lmove(
        self,
        first_list: str,
        second_list: str,
        src: str = "LEFT",
        dest: str = "RIGHT",
    ) -> str | None:
        src_list = self.lists.get(first_list, [])
        if not src_list:
            return None
        value = src_list.pop(0 if src == "LEFT" else -1)
        dest_list = self.lists.setdefault(second_list, [])
        if dest == "RIGHT":
            dest_list.append(value)
        else:
            dest_list.insert(0, value)
        return value

    def blmove(
        self,
        first_list: str,
        second_list: str,
        timeout: float,
        src: str = "LEFT",
        dest: str = "RIGHT",
    ) -> str | None:
        del timeout
        return self.lmove(first_list, second_list, src=src, dest=dest)

    def lrem(self, name: str, count: int, value: str) -> int:
        items = self.lists.get(name, [])
        removed = 0
        while count != 0 and value in items:
            items.remove(value)
            removed += 1
            if count > 0:
                count -= 1
        return removed

    def lrange(self, name: str, start: int, end: int) -> list[str]:
        items = self.lists.get(name, [])
        if end == -1:
            return items[start:]
        return items[start : end + 1]


def test_redis_worker_queue_claim_ack() -> None:
    client = FakeRedis()
    queue = RedisRunQueue(client, key_prefix="t", claim_timeout_seconds=0.01)
    worker_queue = RedisWorkerQueue(queue)
    queue.enqueue_run(RunId("run-1"))

    task = worker_queue.claim(block=False)
    assert task == ClaimedTask(run_id=RunId("run-1"), receipt="run-1")
    worker_queue.ack(task)
    assert worker_queue.claim(block=False) is None
