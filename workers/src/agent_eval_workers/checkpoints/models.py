"""Checkpoint value objects — recovery markers, not Domain entities."""

from __future__ import annotations

from dataclasses import dataclass

from agent_eval_domain.common.ids import RunId

from agent_eval_workers.lifecycle.phases import OrchestrationPhase, is_terminal_phase


@dataclass(frozen=True, slots=True)
class RunCheckpoint:
    """Durable recovery marker for a claimed Run's orchestration progress.

    Persistence is performed by a ``CheckpointStore`` adapter — this type
    never talks to Infrastructure itself.
    """

    run_id: RunId
    phase: OrchestrationPhase
    attempt: int = 1

    def __post_init__(self) -> None:
        if self.attempt < 1:
            msg = "attempt must be >= 1"
            raise ValueError(msg)

    @property
    def is_resumable(self) -> bool:
        return not is_terminal_phase(self.phase)
