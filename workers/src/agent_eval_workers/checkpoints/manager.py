"""Checkpoint management — create, restore, identify resumable stages."""

from __future__ import annotations

from dataclasses import dataclass

from agent_eval_domain.common.ids import RunId

from agent_eval_workers.checkpoints.models import RunCheckpoint
from agent_eval_workers.checkpoints.ports import CheckpointStore
from agent_eval_workers.lifecycle.phases import OrchestrationPhase


@dataclass(slots=True)
class CheckpointManager:
    """Coordinates checkpoint create / restore via a store port."""

    store: CheckpointStore

    def create(
        self,
        run_id: RunId,
        phase: OrchestrationPhase,
        *,
        attempt: int = 1,
    ) -> RunCheckpoint:
        checkpoint = RunCheckpoint(run_id=run_id, phase=phase, attempt=attempt)
        self.store.save(checkpoint)
        return checkpoint

    def restore(self, run_id: RunId) -> RunCheckpoint | None:
        """Load the latest marker, if any."""
        return self.store.load(run_id)

    def resumable_phase(self, run_id: RunId) -> OrchestrationPhase | None:
        """Return the phase a replacement worker should resume from, if resumable."""
        checkpoint = self.restore(run_id)
        if checkpoint is None or not checkpoint.is_resumable:
            return None
        return checkpoint.phase

    def clear(self, run_id: RunId) -> None:
        self.store.clear(run_id)
