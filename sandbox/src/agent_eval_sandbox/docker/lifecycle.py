"""Docker container lifecycle: create / start / stop / destroy."""

from __future__ import annotations

from typing import Any

from agent_eval_sandbox.docker.mounts import build_mounts
from agent_eval_sandbox.docker.networking import resolve_network
from agent_eval_sandbox.docker.resources import build_resource_host_config
from agent_eval_sandbox.exceptions import (
    SandboxCleanupError,
    SandboxProvisionError,
    SandboxStateError,
)
from agent_eval_sandbox.models import SandboxHandle, SandboxSpec, SandboxState
from agent_eval_sandbox.ports import DockerEngine

_MANAGED_LABEL = "evalforge.sandbox"
_MANAGED_LABEL_VALUE = "true"


def create_container(engine: DockerEngine, spec: SandboxSpec) -> SandboxHandle:
    """Provision a stopped container from ``spec``."""
    try:
        host_config = _build_host_config(spec)
        network_mode, networking_config, dns = resolve_network(spec.network)
        if dns is not None:
            host_config["Dns"] = dns

        labels = {
            **dict(spec.labels),
            _MANAGED_LABEL: _MANAGED_LABEL_VALUE,
        }
        container_id = engine.create_container(
            image=spec.image,
            name=spec.name,
            command=list(spec.command),
            working_dir=spec.working_dir,
            environment=dict(spec.environment),
            labels=labels,
            host_config=host_config,
            networking_config=networking_config,
            network_mode=network_mode,
        )
    except SandboxProvisionError:
        raise
    except Exception as exc:  # noqa: BLE001 — normalize Docker failures
        raise SandboxProvisionError(
            f"Failed to create sandbox container: {exc}",
            details={"image": spec.image},
            cause=exc,
        ) from exc

    return SandboxHandle(
        id=SandboxHandle.new_id(),
        container_id=container_id,
        state=SandboxState.CREATED,
        spec=spec,
    )


def start_container(engine: DockerEngine, handle: SandboxHandle) -> SandboxHandle:
    _require_state(handle, {SandboxState.CREATED, SandboxState.STOPPED}, "start")
    try:
        engine.start_container(handle.container_id)
    except Exception as exc:  # noqa: BLE001
        raise SandboxProvisionError(
            f"Failed to start sandbox {handle.id}: {exc}",
            details={"sandbox_id": handle.id, "container_id": handle.container_id},
            cause=exc,
        ) from exc
    return handle.with_state(SandboxState.STARTED)


def stop_container(
    engine: DockerEngine,
    handle: SandboxHandle,
    *,
    timeout: float | None = None,
) -> SandboxHandle:
    if handle.state is SandboxState.DESTROYED:
        raise SandboxStateError(
            f"Cannot stop destroyed sandbox {handle.id}",
            details={"sandbox_id": handle.id, "state": handle.state.value},
        )
    if handle.state is SandboxState.CREATED:
        return handle.with_state(SandboxState.STOPPED)
    if handle.state is SandboxState.STOPPED:
        return handle

    # Stop grace is independent of execution timeout (often 300s). Long-lived
    # entrypoints like `sleep infinity` ignore SIGTERM; keep grace short so
    # teardown reaches force-remove promptly.
    stop_timeout = timeout if timeout is not None else 10.0
    try:
        engine.stop_container(handle.container_id, timeout=float(stop_timeout))
    except Exception as exc:  # noqa: BLE001
        # Force path still proceeds via destroy; surface as provision/stop failure.
        raise SandboxProvisionError(
            f"Failed to stop sandbox {handle.id}: {exc}",
            details={"sandbox_id": handle.id, "container_id": handle.container_id},
            cause=exc,
        ) from exc
    return handle.with_state(SandboxState.STOPPED)


def destroy_container(engine: DockerEngine, handle: SandboxHandle) -> SandboxHandle:
    """Force-remove the container. Idempotent for DESTROYED."""
    if handle.state is SandboxState.DESTROYED:
        return handle
    try:
        engine.remove_container(handle.container_id, force=True)
    except Exception as exc:  # noqa: BLE001
        # Treat "already gone" as success when message indicates missing container.
        message = str(exc).lower()
        if "no such container" not in message and "not found" not in message:
            raise SandboxCleanupError(
                f"Failed to destroy sandbox {handle.id}: {exc}",
                details={
                    "sandbox_id": handle.id,
                    "container_id": handle.container_id,
                },
                cause=exc,
            ) from exc
    return handle.with_state(SandboxState.DESTROYED)


def _build_host_config(spec: SandboxSpec) -> dict[str, Any]:
    config = build_resource_host_config(spec.resources)
    mounts = build_mounts(spec.mounts)
    if mounts:
        config["Mounts"] = mounts
    return config


def _require_state(
    handle: SandboxHandle,
    allowed: set[SandboxState],
    operation: str,
) -> None:
    if handle.state not in allowed:
        raise SandboxStateError(
            f"Cannot {operation} sandbox {handle.id} in state {handle.state.value}",
            details={
                "sandbox_id": handle.id,
                "state": handle.state.value,
                "allowed": sorted(s.value for s in allowed),
            },
        )
