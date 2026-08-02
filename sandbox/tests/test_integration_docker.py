"""Optional live-Docker integration tests (skipped without a daemon)."""

from __future__ import annotations

import shutil

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
def live_manager() -> SandboxManager:
    if not _docker_available():
        pytest.skip("Docker daemon not available")
    engine = DockerPyEngine.from_env()
    # Ensure a tiny image exists for the test.
    engine.client.images.pull("busybox:1.36")
    return SandboxManager(runtime=DockerSandbox(engine=engine))


def test_live_create_execute_cleanup(live_manager: SandboxManager) -> None:
    spec = SandboxSpec(
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
    )
    with live_manager.session(spec) as handle:
        result = live_manager.execute(
            handle,
            ExecutionRequest(command=("echo", "evalforge-sandbox")),
        )
        assert result.exit_code == 0
        assert "evalforge-sandbox" in result.stdout
        assert result.timed_out is False
