"""In-memory checkpoint store for tests (no Infrastructure)."""

from __future__ import annotations

from agent_eval_domain.common.ids import RunId

from agent_eval_workers.checkpoints.models import RunCheckpoint


class InMemoryCheckpointStore:
    """Process-local checkpoint dictionary."""

    def __init__(self) -> None:
        self._items: dict[str, RunCheckpoint] = {}

    def save(self, checkpoint: RunCheckpoint) -> None:
        self._items[checkpoint.run_id.value] = checkpoint

    def load(self, run_id: RunId) -> RunCheckpoint | None:
        return self._items.get(run_id.value)

    def clear(self, run_id: RunId) -> None:
        self._items.pop(run_id.value, None)
