"""Run lifecycle and grading commands."""

from __future__ import annotations

from dataclasses import dataclass, field
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


@dataclass(frozen=True, slots=True)
class CancelRunCommand:
    actor: Actor
    run_id: str
    reason: str | None = None


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
