"""Immutable ExecutionContext handed to every Adapter invocation."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from agent_eval_sandbox.models import SandboxHandle

from agent_eval_adapters.sdk.models import RunMetadata
from agent_eval_adapters.sdk.ports import (
    AdapterLogger,
    CancellationPort,
    SandboxExecPort,
)


@dataclass(frozen=True, slots=True)
class ExecutionConfig:
    """Per-invocation execution bounds (not Domain business rules)."""

    timeout_seconds: float = 600.0
    artifact_inline_max_bytes: int = 8_192
    stream_idle_timeout_seconds: float | None = None


@dataclass(frozen=True, slots=True)
class ExecutionContext:
    """Everything an Adapter needs for one invocation.

    Immutable after creation — Adapters must not mutate and must not retain
    context across invocations (Adapter Architecture — pure boundary).
    """

    working_directory: str
    sandbox: SandboxHandle
    sandbox_exec: SandboxExecPort
    environment: Mapping[str, str]
    run: RunMetadata
    correlation_id: str
    config: ExecutionConfig = field(default_factory=ExecutionConfig)
    prompt: str = ""
    logger: AdapterLogger | None = None
    cancellation: CancellationPort | None = None

    def __post_init__(self) -> None:
        # Freeze mappings so callers cannot mutate after construction.
        object.__setattr__(
            self,
            "environment",
            MappingProxyType(dict(self.environment)),
        )

    def is_cancelled(self) -> bool:
        if self.cancellation is None:
            return False
        return self.cancellation.is_cancelled()
