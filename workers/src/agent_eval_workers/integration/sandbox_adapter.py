"""SandboxPort ← SandboxManager / DockerSandbox (Engine stays Docker-unaware)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from agent_eval_domain.common.ids import RunId
from agent_eval_sandbox.exceptions import SandboxError
from agent_eval_sandbox.manager import SandboxManager
from agent_eval_sandbox.models import SandboxHandle, SandboxSpec, SandboxState

from agent_eval_workers.execution_engine.errors import RecoverableExecutionError
from agent_eval_workers.integration.registry import RunSandboxRegistry
from agent_eval_workers.lifecycle.triggers import FailureCause

SpecFactory = Callable[[RunId], SandboxSpec]
ProvisionHook = Callable[[RunId], None]


def default_sandbox_spec(run_id: RunId) -> SandboxSpec:
    return SandboxSpec(
        image="agent-eval/sandbox:test",
        working_dir="/workspace",
        labels={"run_id": run_id.value},
        name=f"run-{run_id.value}"[:63],
    )


@dataclass
class ManagedSandboxAdapter:
    """``SandboxPort`` backed by ``SandboxManager`` — never leaks Docker types
    into the Execution Engine.
    """

    manager: SandboxManager
    registry: RunSandboxRegistry
    spec_factory: SpecFactory = field(default=default_sandbox_spec)
    fail_on_provision: bool = False
    after_provision: ProvisionHook | None = None
    provisioned: list[RunId] = field(default_factory=list)
    destroyed: list[RunId] = field(default_factory=list)

    def provision(self, run_id: RunId) -> None:
        if self.fail_on_provision:
            raise RecoverableExecutionError(
                f"Sandbox provision failed for {run_id.value}",
                cause=FailureCause.SANDBOX_FAILURE,
            )
        try:
            spec = self.spec_factory(run_id)
            handle = self.manager.create(spec)
            handle = self.manager.start(handle)
            self.registry.register(run_id, handle)
            self.provisioned.append(run_id)
        except SandboxError as exc:
            raise RecoverableExecutionError(
                f"Sandbox provision failed for {run_id.value}: {exc}",
                cause=FailureCause.SANDBOX_FAILURE,
            ) from exc
        except Exception as exc:  # noqa: BLE001
            raise RecoverableExecutionError(
                f"Sandbox provision failed for {run_id.value}: {exc}",
                cause=FailureCause.SANDBOX_FAILURE,
            ) from exc
        if self.after_provision is not None:
            self.after_provision(run_id)

    def destroy(self, run_id: RunId) -> None:
        handle = self.registry.pop(run_id)
        self.destroyed.append(run_id)
        if handle is None:
            return
        try:
            if handle.state not in {SandboxState.STOPPED, SandboxState.DESTROYED}:
                try:
                    handle = self.manager.stop(handle)
                except Exception:  # noqa: BLE001 — best-effort stop before destroy
                    pass
            self.manager.destroy(handle)
        except Exception:  # noqa: BLE001 — teardown must not mask original failure
            pass

    def handle_for(self, run_id: RunId) -> SandboxHandle:
        return self.registry.get(run_id)

    def is_ready(self, run_id: RunId) -> bool:
        return self.registry.has(run_id)
