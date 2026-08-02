"""SDK value objects — native observations and emission payloads."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from agent_eval_domain.execution.normalized_model import NormalizedAction


class ObservationKind(StrEnum):
    TOOL_INVOCATION = "tool_invocation"
    STDOUT = "stdout"
    STDERR = "stderr"
    FILE_CHANGE = "file_change"
    COMPLETION = "completion"
    ERROR = "error"
    MESSAGE = "message"
    SHELL_COMMAND = "shell_command"


class AdapterOutcome(StrEnum):
    """How Agent execution concluded — not evaluative grading."""

    COMPLETED = "completed"
    AGENT_FAILED = "agent_failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"
    ADAPTER_FAILED = "adapter_failed"


@dataclass(frozen=True, slots=True)
class NativeObservation:
    """Vendor-agnostic observation envelope before NDM translation."""

    kind: ObservationKind
    timestamp: datetime
    payload: Mapping[str, Any] = field(default_factory=dict)
    raw: str | None = None


@dataclass(frozen=True, slots=True)
class EmittedEvent:
    """One translated Execution Event handed across the reporting boundary."""

    event_id: str
    action: NormalizedAction
    observed_at: datetime
    artifact_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class EmittedArtifact:
    """Opaque artifact payload for the Execution Engine to persist."""

    artifact_id: str
    kind: str
    content: bytes
    content_type: str = "application/octet-stream"
    metadata: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class EmittedProgress:
    """Non-durable progress hint (not an Execution Event)."""

    message: str
    percent: float | None = None


@dataclass(frozen=True, slots=True)
class RunMetadata:
    """Pinned identities the adapter may need for logging / event ids only."""

    run_id: str
    agent_version_id: str
    adapter_version_id: str
    prompt_version_id: str
    case_version_id: str | None = None
