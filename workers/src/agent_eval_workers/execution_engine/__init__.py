"""Execution Engine — orchestration authority for a single Run.

Responsibility (Execution Engine Architecture):
- Own the step sequence from worker pickup through terminal completion
- Drive the Run lifecycle with cooperative cancel / timeout checks
- Create recovery checkpoints at durable step boundaries
- Report classified failures to the Worker (Worker owns retry policy)

Must NOT:
- Contain vendor-specific translation (Adapter Layer)
- Contain scoring / rubric judgment (Grader Layer)
- Own queue leases, ack/release, or retry budgets (Worker)
- Talk to PostgreSQL, object storage, or the queue directly
- Own authorization or API-facing concerns
"""

from agent_eval_workers.execution_engine.engine import ExecutionEngine
from agent_eval_workers.execution_engine.errors import RecoverableExecutionError
from agent_eval_workers.execution_engine.lifecycle_driver import LifecycleDriver
from agent_eval_workers.execution_engine.results import EngineOutcomeKind, EngineResult
from agent_eval_workers.execution_engine.sequence import (
    happy_path_triggers_from,
    next_happy_path_trigger,
)

__all__ = [
    "EngineOutcomeKind",
    "EngineResult",
    "ExecutionEngine",
    "LifecycleDriver",
    "RecoverableExecutionError",
    "happy_path_triggers_from",
    "next_happy_path_trigger",
]
