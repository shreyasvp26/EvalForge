"""Worker-facing queue port — claim / ack / release / lease (no broker specifics).

Application ``RunQueue`` only enqueues. Workers consume through this wider
operational contract (Execution Engine Architecture — Worker Model).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from agent_eval_domain.common.ids import RunId


@dataclass(frozen=True, slots=True)
class ClaimedTask:
    """A Run task currently leased by a worker."""

    run_id: RunId
    receipt: str = ""
    """Opaque lease token supplied by the broker adapter (optional)."""


class WorkerQueuePort(Protocol):
    """Operational queue surface for the Worker chassis."""

    def claim(self, *, block: bool = True) -> ClaimedTask | None:
        """Acquire the next eligible task, or ``None`` when idle."""
        ...

    def ack(self, task: ClaimedTask) -> None:
        """Acknowledge successful handling — remove from processing."""
        ...

    def release(self, task: ClaimedTask) -> None:
        """Return the task for redelivery (retry / crash recovery)."""
        ...

    def heartbeat(self, task: ClaimedTask) -> None:
        """Signal the worker is still processing the leased task."""
        ...

    def extend_visibility(self, task: ClaimedTask, *, seconds: float) -> None:
        """Extend the lease / visibility window while work continues."""
        ...
