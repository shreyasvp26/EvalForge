"""Run lifecycle and grading commands."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from agent_eval_application.common.actor import Actor


@dataclass(frozen=True, slots=True)
class CreateRunCommand:
    """Create and queue a Run. Returns once queued — never after execution."""

    actor: Actor
    project_id: str
    case_id: str
    case_version_id: str
    prompt_version_id: str
    agent_id: str
    agent_version_id: str
    adapter_version_id: str
    grader_version_refs: tuple[tuple[str, str], ...]
    """Pairs of (grader_id, grader_version_id)."""
    platform_version_id: str
    suite_id: str | None = None
    suite_version_id: str | None = None
    idempotency_key: str | None = None


@dataclass(frozen=True, slots=True)
class StartRunCommand:
    """Worker advances Queued → Running with a provisioned sandbox id."""

    actor: Actor
    run_id: str
    sandbox_id: str


@dataclass(frozen=True, slots=True)
class StartGradingCommand:
    actor: Actor
    run_id: str


@dataclass(frozen=True, slots=True)
class CompleteRunCommand:
    actor: Actor
    run_id: str


@dataclass(frozen=True, slots=True)
class FailRunCommand:
    """Platform-caused failure — distinct from low Scores on Completed."""

    actor: Actor
    run_id: str
    reason: str
    category: str | None = None
    """Optional ``FailureCategory`` value (e.g. ``adapter_failure``)."""


@dataclass(frozen=True, slots=True)
class CancelRunCommand:
    actor: Actor
    run_id: str
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class RecordRunTelemetryCommand:
    """Persist wall-clock / optional provider usage once per Run.

    Token and cost fields must only be set when the provider actually exposed
    reliable usage. Never fabricate estimated_cost.
    """

    actor: Actor
    run_id: str
    wall_clock_ms: int = 0
    compute_ms: int = 0
    input_tokens: int | None = None
    output_tokens: int | None = None
    provider_usage_available: bool = False


@dataclass(frozen=True, slots=True)
class RecordExecutionConfigurationCommand:
    """Persist the effective execution configuration used for a Run.

    Must never include secrets, API keys, or credential-bearing env values.
    """

    actor: Actor
    run_id: str
    execution_mode: str
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RecordScoreCommand:
    """Persist a Score produced by the Grader Layer via Application."""

    actor: Actor
    run_id: str
    grader_id: str
    grader_version_id: str
    numeric: float | None = None
    categorical: str | None = None
    passed: bool | None = None
    detail: dict[str, Any] = field(default_factory=dict)
    explanation_artifact_id: str | None = None


@dataclass(frozen=True, slots=True)
class RecordArtifactCommand:
    actor: Actor
    run_id: str
    kind: str
    storage_key: str
    content_type: str
    size_bytes: int
    checksum: str
    produced_by_grader_version_id: str | None = None
    artifact_id: str | None = None
    """Stable client id for idempotent retries; generated when omitted."""


@dataclass(frozen=True, slots=True)
class RecordExecutionEventCommand:
    """Append one Execution Event via Application (Worker / Engine path)."""

    actor: Actor
    run_id: str
    execution_event_id: str
    """Stable id — duplicate deliveries with the same id are no-ops."""
    action: dict[str, Any]
    """NDM action payload including ``kind`` (see Domain ``ndm_codec``)."""
    artifact_ids: tuple[str, ...] = ()
    metadata: dict[str, str] = field(default_factory=dict)
    occurred_at: datetime | None = None
    """Optional timestamp; ``None`` lets Domain assign ``utc_now``."""
