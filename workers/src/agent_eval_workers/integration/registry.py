"""Shared per-Run sandbox handle registry for Worker composition bridges."""

from __future__ import annotations

from dataclasses import dataclass, field

from agent_eval_domain.common.ids import RunId
from agent_eval_sandbox.models import SandboxHandle


@dataclass
class RunSandboxRegistry:
    """Maps Run → live SandboxHandle without exposing Docker to the Engine."""

    _by_run: dict[str, SandboxHandle] = field(default_factory=dict)

    def register(self, run_id: RunId, handle: SandboxHandle) -> None:
        self._by_run[run_id.value] = handle

    def get(self, run_id: RunId) -> SandboxHandle:
        try:
            return self._by_run[run_id.value]
        except KeyError as exc:
            raise KeyError(f"No sandbox registered for run {run_id.value}") from exc

    def pop(self, run_id: RunId) -> SandboxHandle | None:
        return self._by_run.pop(run_id.value, None)

    def has(self, run_id: RunId) -> bool:
        return run_id.value in self._by_run
