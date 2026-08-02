"""Cancellation observation port — cooperative stop signals."""

from __future__ import annotations

from typing import Protocol

from agent_eval_domain.common.ids import RunId


class CancellationPort(Protocol):
    """Read-side signal that a Run should stop at the next safe boundary."""

    def is_cancel_requested(self, run_id: RunId) -> bool: ...
