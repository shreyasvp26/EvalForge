"""Checkpoint store port — Worker/Engine recovery markers (no direct I/O)."""

from __future__ import annotations

from typing import Protocol

from agent_eval_domain.common.ids import RunId

from agent_eval_workers.checkpoints.models import RunCheckpoint


class CheckpointStore(Protocol):
    """Persistence boundary for orchestration recovery markers."""

    def save(self, checkpoint: RunCheckpoint) -> None: ...

    def load(self, run_id: RunId) -> RunCheckpoint | None: ...

    def clear(self, run_id: RunId) -> None: ...
