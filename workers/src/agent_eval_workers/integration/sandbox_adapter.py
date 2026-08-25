"""SandboxPort ← SandboxManager / DockerSandbox (Engine stays Docker-unaware)."""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from uuid import uuid4

from agent_eval_domain.common.ids import RunId
from agent_eval_sandbox.exceptions import SandboxError
from agent_eval_sandbox.manager import SandboxManager
from agent_eval_sandbox.models import (
    NetworkMode,
    NetworkPolicy,
    SandboxHandle,
    SandboxSpec,
)

from agent_eval_workers.execution_engine.errors import RecoverableExecutionError
from agent_eval_workers.integration.registry import RunSandboxRegistry
from agent_eval_workers.lifecycle.triggers import FailureCause

SpecFactory = Callable[[RunId], SandboxSpec]
ProvisionHook = Callable[[RunId], None]

# Default production/local Compose image (see infrastructure/docker/Dockerfile.sandbox).
DEFAULT_SANDBOX_IMAGE = "evalforge/sandbox:local"


def sandbox_image_from_env() -> str:
    return os.environ.get("WORKER_SANDBOX_IMAGE", DEFAULT_SANDBOX_IMAGE).strip() or (
        DEFAULT_SANDBOX_IMAGE
    )


def sandbox_environment_from_allowlist(
    *,
    allowlist: str | None = None,
    source: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Inject only explicitly allowed variables into the sandbox.

    Never pass the full host environment into an agent container.
    """
    raw = allowlist
    if raw is None:
        raw = os.environ.get(
            "WORKER_SANDBOX_ENV_ALLOWLIST",
            "ANTHROPIC_API_KEY,GEMINI_API_KEY,GOOGLE_API_KEY,PATH,HOME,TERM",
        )
    keys = [k.strip() for k in raw.split(",") if k.strip()]
    env_source = source if source is not None else os.environ
    out: dict[str, str] = {}
    for key in keys:
        value = env_source.get(key)
        if value is not None and value != "":
            out[key] = value
    return out


def sandbox_network_from_env() -> NetworkPolicy:
    """Default deny. Bridge only when live Claude (or tools) need egress."""
    mode_raw = os.environ.get("WORKER_SANDBOX_NETWORK", "none").strip().lower()
    if mode_raw in {"bridge", "default"}:
        return NetworkPolicy(mode=NetworkMode.BRIDGE)
    return NetworkPolicy(mode=NetworkMode.NONE)


def default_sandbox_spec(run_id: RunId) -> SandboxSpec:
    # Include a unique suffix so deterministic test IDs (and rapid retries) never
    # collide on Docker container names left behind after cleanup races.
    unique = uuid4().hex[:8]
    return SandboxSpec(
        image=sandbox_image_from_env(),
        working_dir="/workspace",
        environment=sandbox_environment_from_allowlist(),
        labels={"run_id": run_id.value, "evalforge.component": "sandbox"},
        name=f"run-{run_id.value}-{unique}"[:63],
        network=sandbox_network_from_env(),
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
            # Do not call manager.stop() first: default stop grace uses the
            # execution timeout (often 300s) and sleep-infinity sandboxes ignore
            # SIGTERM. ensure_destroyed already stops with a short grace then
            # force-removes.
            self.manager.destroy(handle)
        except Exception:  # noqa: BLE001 — teardown must not mask original failure
            pass

    def handle_for(self, run_id: RunId) -> SandboxHandle:
        return self.registry.get(run_id)

    def is_ready(self, run_id: RunId) -> bool:
        return self.registry.has(run_id)
