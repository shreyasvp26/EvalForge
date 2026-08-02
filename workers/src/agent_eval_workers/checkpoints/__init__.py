"""Checkpoints — durable progress markers for crash recovery.

Responsibility (Execution Engine Architecture — worker crash / retry safety):
- Record how far orchestration has progressed for a claimed Run
- Allow a replacement worker to resume without duplicating completed steps
- Identify resumable stages via CheckpointManager

Must NOT:
- Persist directly to Infrastructure (CheckpointStore port only)
- Replace Domain append-only event history
- Store Adapter vendor state
- Decide business outcomes (Engine lifecycle still decides next step)
"""

from agent_eval_workers.checkpoints.manager import CheckpointManager
from agent_eval_workers.checkpoints.memory import InMemoryCheckpointStore
from agent_eval_workers.checkpoints.models import RunCheckpoint
from agent_eval_workers.checkpoints.ports import CheckpointStore

__all__ = [
    "CheckpointManager",
    "CheckpointStore",
    "InMemoryCheckpointStore",
    "RunCheckpoint",
]
