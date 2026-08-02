"""Worker process chassis — queue claim host and Engine invocation boundary.

Responsibility (Execution Engine Architecture / Backend Architecture §4):
- Consume Run tasks from the Application/Infrastructure queue contract
- Provide a running process for the Execution Engine's orchestration
- Own operational concerns: leases, retries, heartbeats, shutdown
- Attach correlation / run / worker identifiers for observability
- Translate process-level failures into Application-mediated lifecycle outcomes

Must NOT:
- Decide what step a Run takes next (Execution Engine owns orchestration)
- Contain Adapter translation or Grader scoring logic
- Talk to the API Layer
- Bypass Application to write business state directly to Infrastructure
- Persist Execution Events / Artifacts itself (event pipeline + Application)
- Mutate Domain Run status directly (lifecycle / status port)
"""

from __future__ import annotations

from typing import Any

from agent_eval_workers.clock import Clock, FakeClock, SystemClock
from agent_eval_workers.worker.memory_queue import InMemoryWorkerQueue
from agent_eval_workers.worker.queue import ClaimedTask, WorkerQueuePort
from agent_eval_workers.worker.retry import RetryAction, RetryPolicy

__all__ = [
    "ClaimedTask",
    "Clock",
    "FakeClock",
    "InMemoryWorkerQueue",
    "RetryAction",
    "RetryPolicy",
    "SystemClock",
    "WorkerQueuePort",
    "WorkerRuntime",
    "WorkerState",
    "default_lifecycle_factory",
]


def __getattr__(name: str) -> Any:
    # Lazy import avoids circular import with execution_engine.orchestration.
    if name in {"WorkerRuntime", "WorkerState", "default_lifecycle_factory"}:
        from agent_eval_workers.worker import runtime as _runtime

        return getattr(_runtime, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
