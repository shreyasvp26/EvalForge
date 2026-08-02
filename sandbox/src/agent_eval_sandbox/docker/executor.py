"""Command execution inside a started Docker sandbox."""

from __future__ import annotations

import time

from agent_eval_sandbox.docker.resources import sample_resource_usage
from agent_eval_sandbox.exceptions import (
    SandboxExecutionError,
    SandboxStateError,
    SandboxTimeoutError,
)
from agent_eval_sandbox.models import (
    ExecutionRequest,
    ExecutionResult,
    ResourceUsage,
    SandboxHandle,
    SandboxState,
)
from agent_eval_sandbox.ports import DockerEngine


def execute_command(
    engine: DockerEngine,
    handle: SandboxHandle,
    request: ExecutionRequest,
) -> ExecutionResult:
    """Run ``request.command`` with timeout and resource sampling."""
    if handle.state is not SandboxState.STARTED:
        raise SandboxStateError(
            f"Cannot execute in sandbox {handle.id} in state {handle.state.value}",
            details={"sandbox_id": handle.id, "state": handle.state.value},
        )
    if not request.command:
        raise SandboxExecutionError(
            "Execution command must be non-empty",
            details={"sandbox_id": handle.id},
        )

    timeout = (
        request.timeout_seconds
        if request.timeout_seconds is not None
        else handle.spec.resources.timeout_seconds
    )
    workdir = request.working_dir or handle.spec.working_dir
    environment = dict(request.environment) if request.environment else None

    started = time.perf_counter()
    usage_before = _safe_stats(engine, handle.container_id)
    try:
        exit_code, stdout_b, stderr_b, timed_out = engine.exec_run(
            handle.container_id,
            command=list(request.command),
            working_dir=workdir,
            environment=environment,
            timeout_seconds=timeout,
        )
    except SandboxTimeoutError:
        duration = time.perf_counter() - started
        usage = _pick_usage(_safe_stats(engine, handle.container_id), duration)
        return ExecutionResult(
            exit_code=124,
            stdout="",
            stderr="sandbox execution timed out",
            duration_seconds=duration,
            timed_out=True,
            resource_usage=usage,
        )
    except SandboxExecutionError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise SandboxExecutionError(
            f"Sandbox execution failed: {exc}",
            details={
                "sandbox_id": handle.id,
                "container_id": handle.container_id,
                "command": list(request.command),
            },
            cause=exc,
        ) from exc

    duration = time.perf_counter() - started
    usage_after = _safe_stats(engine, handle.container_id)
    usage = _pick_usage(usage_after or usage_before, duration)

    return ExecutionResult(
        exit_code=int(exit_code),
        stdout=_decode(stdout_b),
        stderr=_decode(stderr_b),
        duration_seconds=duration,
        timed_out=timed_out,
        resource_usage=usage,
    )


def _safe_stats(engine: DockerEngine, container_id: str) -> dict[str, object] | None:
    try:
        stats = engine.container_stats(container_id)
        return dict(stats)
    except Exception:  # noqa: BLE001 — usage is best-effort
        return None


def _pick_usage(
    stats: dict[str, object] | None,
    duration_seconds: float,
) -> ResourceUsage:
    if stats is None:
        return ResourceUsage(duration_seconds=duration_seconds)
    return sample_resource_usage(stats, duration_seconds=duration_seconds)


def _decode(payload: bytes) -> str:
    return payload.decode("utf-8", errors="replace")
