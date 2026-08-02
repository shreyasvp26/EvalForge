"""Sandbox manager — tracks live sandboxes and guarantees cleanup.

The manager is the preferred entry point for callers that need create/start/
execute/copy_out/stop/destroy plus registry-backed cleanup after timeout,
failure, or worker interruption.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from threading import RLock

from agent_eval_sandbox.exceptions import (
    SandboxCleanupError,
    SandboxNotFoundError,
)
from agent_eval_sandbox.models import (
    ArtifactExport,
    ArtifactExportRequest,
    ExecutionRequest,
    ExecutionResult,
    SandboxHandle,
    SandboxSpec,
    SandboxState,
)
from agent_eval_sandbox.ports import SandboxRuntime


@dataclass
class SandboxManager:
    """Owns sandbox handles for one worker process.

    Always attempts destroy on release, even after timeout / failure /
    interruption — matching Execution Engine Architecture Sandbox Lifecycle.
    """

    runtime: SandboxRuntime
    _handles: dict[str, SandboxHandle] = field(default_factory=dict, init=False)
    _lock: RLock = field(default_factory=RLock, init=False)

    def create(self, spec: SandboxSpec) -> SandboxHandle:
        handle = self.runtime.create(spec)
        with self._lock:
            self._handles[handle.id] = handle
        return handle

    def start(self, handle: SandboxHandle) -> SandboxHandle:
        known = self._require(handle.id)
        updated = self.runtime.start(known)
        return self._store(updated)

    def execute(
        self,
        handle: SandboxHandle,
        request: ExecutionRequest,
    ) -> ExecutionResult:
        known = self._require(handle.id)
        return self.runtime.execute(known, request)

    def copy_out(
        self,
        handle: SandboxHandle,
        request: ArtifactExportRequest,
    ) -> ArtifactExport:
        known = self._require(handle.id)
        return self.runtime.copy_out(known, request)

    def stop(self, handle: SandboxHandle) -> SandboxHandle:
        known = self._require(handle.id)
        updated = self.runtime.stop(known)
        return self._store(updated)

    def destroy(self, handle: SandboxHandle) -> SandboxHandle:
        """Destroy and unregister. Idempotent if already destroyed/missing."""
        with self._lock:
            known = self._handles.get(handle.id, handle)
        try:
            updated = self.runtime.destroy(known)
        finally:
            with self._lock:
                self._handles.pop(handle.id, None)
        return updated

    def get(self, sandbox_id: str) -> SandboxHandle:
        return self._require(sandbox_id)

    def active(self) -> Mapping[str, SandboxHandle]:
        with self._lock:
            return dict(self._handles)

    def cleanup_all(self) -> list[str]:
        """Force-destroy every tracked sandbox. Returns destroyed ids.

        Collects per-sandbox cleanup failures and raises once after attempting
        every remaining handle — never skips remaining sandboxes because one
        destroy failed.
        """
        with self._lock:
            handles = list(self._handles.values())
        failures: list[tuple[str, BaseException]] = []
        destroyed: list[str] = []
        for handle in handles:
            try:
                self.destroy(handle)
                destroyed.append(handle.id)
            except Exception as exc:  # noqa: BLE001 — must continue cleanup
                failures.append((handle.id, exc))
                with self._lock:
                    self._handles.pop(handle.id, None)
        if failures:
            detail = {sid: str(err) for sid, err in failures}
            raise SandboxCleanupError(
                f"Failed to clean up {len(failures)} sandbox(es)",
                details={"failures": detail, "destroyed": destroyed},
            )
        return destroyed

    @contextmanager
    def session(self, spec: SandboxSpec) -> Iterator[SandboxHandle]:
        """Create + start a sandbox; always stop + destroy on exit."""
        handle = self.create(spec)
        try:
            handle = self.start(handle)
            yield handle
        finally:
            self._safe_stop(handle)
            self.destroy(handle)

    def _safe_stop(self, handle: SandboxHandle) -> None:
        try:
            known = self._handles.get(handle.id, handle)
            if known.state in {SandboxState.STARTED}:
                self.stop(known)
        except Exception:  # noqa: BLE001 — destroy still runs
            return

    def _require(self, sandbox_id: str) -> SandboxHandle:
        with self._lock:
            handle = self._handles.get(sandbox_id)
        if handle is None:
            raise SandboxNotFoundError(
                f"Sandbox {sandbox_id!r} is not registered",
                details={"sandbox_id": sandbox_id},
            )
        return handle

    def _store(self, handle: SandboxHandle) -> SandboxHandle:
        with self._lock:
            if handle.id not in self._handles:
                raise SandboxNotFoundError(
                    f"Sandbox {handle.id!r} is not registered",
                    details={"sandbox_id": handle.id},
                )
            self._handles[handle.id] = handle
        return handle
