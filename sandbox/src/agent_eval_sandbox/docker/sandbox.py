"""Docker-backed ``SandboxRuntime`` implementation."""

from __future__ import annotations

import io
import tarfile
from dataclasses import dataclass
from pathlib import Path

from agent_eval_sandbox.docker import cleanup, executor, lifecycle
from agent_eval_sandbox.exceptions import SandboxCopyError, SandboxStateError
from agent_eval_sandbox.models import (
    ArtifactExport,
    ArtifactExportRequest,
    ArtifactKind,
    ExecutionRequest,
    ExecutionResult,
    SandboxHandle,
    SandboxSpec,
    SandboxState,
)
from agent_eval_sandbox.ports import DockerEngine


@dataclass(slots=True)
class DockerSandbox:
    """Production Sandbox Runtime backed by a ``DockerEngine``.

    Knows only containers, mounts, limits, and command execution — never
    Domain, Application, Execution Engine, Adapter, or Grader concepts.
    """

    engine: DockerEngine

    def create(self, spec: SandboxSpec) -> SandboxHandle:
        return lifecycle.create_container(self.engine, spec)

    def start(self, handle: SandboxHandle) -> SandboxHandle:
        return lifecycle.start_container(self.engine, handle)

    def execute(
        self,
        handle: SandboxHandle,
        request: ExecutionRequest,
    ) -> ExecutionResult:
        return executor.execute_command(self.engine, handle, request)

    def copy_out(
        self,
        handle: SandboxHandle,
        request: ArtifactExportRequest,
    ) -> ArtifactExport:
        if handle.state is SandboxState.DESTROYED:
            raise SandboxStateError(
                f"Cannot copy_out from destroyed sandbox {handle.id}",
                details={"sandbox_id": handle.id},
            )
        if not request.container_path:
            raise SandboxCopyError(
                "container_path must be non-empty",
                details={"sandbox_id": handle.id},
            )

        try:
            archive = self.engine.get_archive(
                handle.container_id,
                request.container_path,
            )
        except Exception as exc:  # noqa: BLE001
            raise SandboxCopyError(
                f"Failed to archive {request.container_path!r}: {exc}",
                details={
                    "sandbox_id": handle.id,
                    "container_id": handle.container_id,
                    "path": request.container_path,
                    "kind": request.kind.value,
                },
                cause=exc,
            ) from exc

        content = _extract_content(archive, request)
        destination = request.destination
        if destination is not None:
            path = Path(destination)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)

        return ArtifactExport(
            container_path=request.container_path,
            kind=request.kind,
            size_bytes=len(content),
            content=content,
            destination=destination,
        )

    def stop(self, handle: SandboxHandle) -> SandboxHandle:
        return lifecycle.stop_container(self.engine, handle)

    def destroy(self, handle: SandboxHandle) -> SandboxHandle:
        return cleanup.ensure_destroyed(self.engine, handle)


def _extract_content(archive: bytes, request: ArtifactExportRequest) -> bytes:
    if request.kind is ArtifactKind.DIRECTORY:
        return archive

    try:
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:*") as tar:
            members = [m for m in tar.getmembers() if m.isfile()]
            if not members:
                return archive
            chunks: list[bytes] = []
            for member in members:
                extracted = tar.extractfile(member)
                if extracted is None:
                    continue
                chunks.append(extracted.read())
            if len(chunks) == 1:
                return chunks[0]
            return b"".join(chunks)
    except tarfile.TarError as exc:
        raise SandboxCopyError(
            f"Invalid archive for {request.container_path!r}: {exc}",
            details={"path": request.container_path, "kind": request.kind.value},
            cause=exc,
        ) from exc
