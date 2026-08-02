"""Deterministic mock Sandbox for orchestration verification."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from agent_eval_domain.common.ids import RunId

from agent_eval_workers.execution_engine.errors import RecoverableExecutionError
from agent_eval_workers.lifecycle.triggers import FailureCause

ProvisionHook = Callable[[RunId], None]


@dataclass
class MockSandbox:
    """In-memory Sandbox — provision / ready / teardown only."""

    fail_on_provision: bool = False
    after_provision: ProvisionHook | None = None
    provisioned: list[RunId] = field(default_factory=list)
    destroyed: list[RunId] = field(default_factory=list)
    _ready: set[str] = field(default_factory=set)

    def provision(self, run_id: RunId) -> None:
        if self.fail_on_provision:
            raise RecoverableExecutionError(
                f"Mock sandbox provision failed for {run_id.value}",
                cause=FailureCause.SANDBOX_FAILURE,
            )
        self.provisioned.append(run_id)
        self._ready.add(run_id.value)
        if self.after_provision is not None:
            self.after_provision(run_id)

    def destroy(self, run_id: RunId) -> None:
        self._ready.discard(run_id.value)
        self.destroyed.append(run_id)

    def is_ready(self, run_id: RunId) -> bool:
        return run_id.value in self._ready
