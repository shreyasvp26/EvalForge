"""Adapter SDK ports — reporting and sandbox observation only."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, runtime_checkable

from agent_eval_sandbox.models import ExecutionRequest, ExecutionResult, SandboxHandle

from agent_eval_adapters.sdk.models import (
    EmittedArtifact,
    EmittedEvent,
    EmittedProgress,
)


@runtime_checkable
class EventSink(Protocol):
    """Reporting channel to the Execution Engine.

    Implementations must NOT write to repositories or object storage.
    """

    def on_event(self, event: EmittedEvent) -> None: ...

    def on_artifact(self, artifact: EmittedArtifact) -> None: ...

    def on_progress(self, progress: EmittedProgress) -> None: ...

    def on_error(
        self,
        message: str,
        *,
        details: Mapping[str, object] | None = None,
    ) -> None: ...


@runtime_checkable
class SandboxExecPort(Protocol):
    """Minimal sandbox surface an Adapter may use for observation / commands."""

    def execute(
        self,
        handle: SandboxHandle,
        request: ExecutionRequest,
    ) -> ExecutionResult: ...


@runtime_checkable
class CancellationPort(Protocol):
    """Cooperative cancellation signal owned by the caller (Execution Engine)."""

    def is_cancelled(self) -> bool: ...


@runtime_checkable
class AdapterLogger(Protocol):
    """Structured logger injected via ExecutionContext (Shared concern)."""

    def info(self, message: str, **fields: object) -> None: ...

    def warning(self, message: str, **fields: object) -> None: ...

    def error(self, message: str, **fields: object) -> None: ...
