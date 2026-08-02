"""Run execution queue contract.

When Application creates a Run and transitions it to Queued, it publishes a
task through this port — never a concrete broker (Backend Architecture §7).
"""

from __future__ import annotations

from typing import Protocol

from agent_eval_domain.common.ids import RunId


class RunQueue(Protocol):
    """Enqueue work for Background Workers to execute a Run."""

    def enqueue_run(self, run_id: RunId) -> None: ...
