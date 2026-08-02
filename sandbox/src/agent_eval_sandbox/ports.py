"""Sandbox Runtime ports.

The Execution Engine (and tests) depend on these contracts — never on Docker
internals. A future non-Docker sandbox implements the same ``SandboxRuntime``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, runtime_checkable

from agent_eval_sandbox.models import (
    ArtifactExport,
    ArtifactExportRequest,
    ExecutionRequest,
    ExecutionResult,
    SandboxHandle,
    SandboxSpec,
)


@runtime_checkable
class SandboxRuntime(Protocol):
    """Isolated execution: create → start → execute/copy_out → stop → destroy."""

    def create(self, spec: SandboxSpec) -> SandboxHandle:
        """Provision a container (not yet running)."""
        ...

    def start(self, handle: SandboxHandle) -> SandboxHandle:
        """Start a created sandbox."""
        ...

    def execute(
        self,
        handle: SandboxHandle,
        request: ExecutionRequest,
    ) -> ExecutionResult:
        """Run a command; return exit code, stdout/stderr, duration, usage."""
        ...

    def copy_out(
        self,
        handle: SandboxHandle,
        request: ArtifactExportRequest,
    ) -> ArtifactExport:
        """Export a file, directory, or log from the sandbox."""
        ...

    def stop(self, handle: SandboxHandle) -> SandboxHandle:
        """Stop a running sandbox (container retained until destroy)."""
        ...

    def destroy(self, handle: SandboxHandle) -> SandboxHandle:
        """Force-remove the container. Idempotent for already-destroyed handles."""
        ...


@runtime_checkable
class DockerEngine(Protocol):
    """Thin Docker API surface used by the Docker sandbox implementation.

    Tests inject a fake; production wraps ``docker.DockerClient``.
    """

    def create_container(
        self,
        *,
        image: str,
        name: str | None,
        command: list[str],
        working_dir: str,
        environment: Mapping[str, str],
        labels: Mapping[str, str],
        host_config: Mapping[str, object],
        networking_config: Mapping[str, object] | None = None,
        network_mode: str | None = None,
    ) -> str:
        """Create a container; return container id."""
        ...

    def start_container(self, container_id: str) -> None: ...

    def stop_container(self, container_id: str, *, timeout: float) -> None: ...

    def remove_container(self, container_id: str, *, force: bool = True) -> None: ...

    def exec_run(
        self,
        container_id: str,
        *,
        command: list[str],
        working_dir: str | None,
        environment: Mapping[str, str] | None,
        timeout_seconds: float | None,
    ) -> tuple[int, bytes, bytes, bool]:
        """Return ``(exit_code, stdout, stderr, timed_out)``."""
        ...

    def get_archive(self, container_id: str, path: str) -> bytes:
        """Return a tar archive of ``path`` inside the container."""
        ...

    def container_stats(self, container_id: str) -> Mapping[str, object]:
        """One-shot container stats snapshot."""
        ...
