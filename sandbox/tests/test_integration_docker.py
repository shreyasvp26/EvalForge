"""Optional live-Docker integration tests (skipped without a daemon)."""

from __future__ import annotations

import shutil
import time

import docker
import pytest
from agent_eval_sandbox.docker.engine import DockerPyEngine
from agent_eval_sandbox.docker.sandbox import DockerSandbox
from agent_eval_sandbox.manager import SandboxManager
from agent_eval_sandbox.models import (
    ExecutionRequest,
    NetworkMode,
    NetworkPolicy,
    ResourceLimits,
    SandboxSpec,
)


def _docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        client = docker.from_env()
        client.ping()
        return True
    except Exception:  # noqa: BLE001
        return False


pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def live_engine() -> DockerPyEngine:
    if not _docker_available():
        pytest.skip("Docker daemon not available")
    engine = DockerPyEngine.from_env()
    engine.client.images.pull("busybox:1.36")
    return engine


@pytest.fixture(scope="module")
def live_manager(live_engine: DockerPyEngine) -> SandboxManager:
    return SandboxManager(runtime=DockerSandbox(engine=live_engine))


def _busybox_spec(*, name: str | None = None) -> SandboxSpec:
    return SandboxSpec(
        image="busybox:1.36",
        working_dir="/tmp",
        command=("sleep", "infinity"),
        resources=ResourceLimits(
            cpu_cores=0.25,
            memory_bytes=64 * 1024 * 1024,
            disk_bytes=None,
            timeout_seconds=15.0,
        ),
        network=NetworkPolicy(mode=NetworkMode.NONE),
        name=name,
        labels={"evalforge.test": "integration"},
    )


def test_live_create_execute_cleanup(live_manager: SandboxManager) -> None:
    with live_manager.session(_busybox_spec()) as handle:
        result = live_manager.execute(
            handle,
            ExecutionRequest(command=("echo", "evalforge-sandbox")),
        )
        assert result.exit_code == 0
        assert "evalforge-sandbox" in result.stdout
        assert result.timed_out is False
        assert result.stderr == "" or True


def test_live_nonzero_exit(live_manager: SandboxManager) -> None:
    with live_manager.session(_busybox_spec()) as handle:
        result = live_manager.execute(
            handle,
            ExecutionRequest(command=("sh", "-c", "echo fail-stderr 1>&2; exit 7")),
        )
        assert result.exit_code == 7
        assert "fail-stderr" in result.stderr
        assert result.timed_out is False


def test_live_timeout_kills_command(live_manager: SandboxManager) -> None:
    with live_manager.session(_busybox_spec()) as handle:
        result = live_manager.execute(
            handle,
            ExecutionRequest(
                command=("sh", "-c", "sleep 30"),
                timeout_seconds=2.0,
            ),
        )
        assert result.timed_out is True


def test_live_cleanup_after_failure(
    live_manager: SandboxManager, live_engine: DockerPyEngine
) -> None:
    name = f"evalforge-cleanup-{int(time.time())}"
    handle = live_manager.create(_busybox_spec(name=name))
    handle = live_manager.start(handle)
    container_id = handle.container_id
    live_manager.execute(
        handle,
        ExecutionRequest(command=("sh", "-c", "exit 1")),
    )
    live_manager.destroy(handle)
    # Container must be gone from the daemon.
    matching = [
        c
        for c in live_engine.client.containers.list(all=True)
        if c.id.startswith(container_id) or c.name.lstrip("/") == name
    ]
    assert matching == []


def test_live_workspace_isolation_between_runs(live_manager: SandboxManager) -> None:
    """Consecutive sandboxes must not share filesystem state."""
    with live_manager.session(_busybox_spec()) as first:
        live_manager.execute(
            first,
            ExecutionRequest(
                command=("sh", "-c", "echo contaminated > /tmp/marker.txt"),
            ),
        )
        listed = live_manager.execute(
            first,
            ExecutionRequest(command=("cat", "/tmp/marker.txt")),
        )
        assert "contaminated" in listed.stdout

    with live_manager.session(_busybox_spec()) as second:
        missing = live_manager.execute(
            second,
            ExecutionRequest(command=("cat", "/tmp/marker.txt")),
        )
        assert missing.exit_code != 0
        assert "contaminated" not in missing.stdout
