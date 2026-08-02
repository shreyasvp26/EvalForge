"""Cleanup guarantees for Docker sandboxes.

Teardown is mandatory after completion, timeout, failure, or worker
interruption (Execution Engine Architecture — Sandbox Lifecycle).
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager

from agent_eval_sandbox.docker import lifecycle
from agent_eval_sandbox.exceptions import SandboxCleanupError
from agent_eval_sandbox.models import SandboxHandle, SandboxState
from agent_eval_sandbox.ports import DockerEngine


def ensure_destroyed(
    engine: DockerEngine,
    handle: SandboxHandle,
) -> SandboxHandle:
    """Best-effort stop + force destroy. Never leaves a live container behind."""
    current = handle
    if current.state is SandboxState.DESTROYED:
        return current

    if current.state is SandboxState.STARTED:
        try:
            current = lifecycle.stop_container(engine, current, timeout=5.0)
        except Exception:  # noqa: BLE001 — destroy still required
            pass

    try:
        return lifecycle.destroy_container(engine, current)
    except SandboxCleanupError:
        # Retry once with force remove semantics already applied.
        try:
            engine.remove_container(current.container_id, force=True)
            return current.with_state(SandboxState.DESTROYED)
        except Exception as exc:  # noqa: BLE001
            raise SandboxCleanupError(
                f"Failed to ensure destruction of sandbox {handle.id}: {exc}",
                details={
                    "sandbox_id": handle.id,
                    "container_id": handle.container_id,
                },
                cause=exc,
            ) from exc


@contextmanager
def cleanup_guard(
    engine: DockerEngine,
    handle: SandboxHandle,
) -> Iterator[SandboxHandle]:
    """Yield ``handle`` and always run ``ensure_destroyed`` on exit."""
    try:
        yield handle
    finally:
        ensure_destroyed(engine, handle)


def run_with_cleanup[T](
    engine: DockerEngine,
    handle: SandboxHandle,
    operation: Callable[[SandboxHandle], T],
) -> T:
    """Run ``operation``; destroy the sandbox even if the operation raises."""
    try:
        return operation(handle)
    finally:
        ensure_destroyed(engine, handle)
