"""Execution Event, Artifact, Score, Sandbox, and Run cost value objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from agent_eval_domain.common.errors import InvariantViolation
from agent_eval_domain.common.events import utc_now
from agent_eval_domain.common.ids import (
    ArtifactId,
    ExecutionEventId,
    GraderId,
    GraderVersionId,
    RunId,
    SandboxId,
    ScoreId,
)
from agent_eval_domain.execution.normalized_model import (
    ActionKind,
    NormalizedAction,
    action_kind_of,
)


@dataclass(frozen=True, slots=True)
class ExecutionCost:
    """Intrinsic cost facts on a Run (Invariant 15). Written once during execution."""

    input_tokens: int = 0
    output_tokens: int = 0
    wall_clock_ms: int = 0
    compute_ms: int = 0

    def __post_init__(self) -> None:
        for field_name in (
            "input_tokens",
            "output_tokens",
            "wall_clock_ms",
            "compute_ms",
        ):
            value = getattr(self, field_name)
            if value < 0:
                raise InvariantViolation(
                    f"{field_name} cannot be negative",
                    code="INVALID_COST",
                    details={field_name: value},
                )


class ArtifactKind(StrEnum):
    DIFF = "diff"
    LOG = "log"
    TRANSCRIPT = "transcript"
    STDOUT = "stdout"
    STDERR = "stderr"
    RUBRIC_EXPLANATION = "rubric_explanation"
    OTHER = "other"


@dataclass(frozen=True, slots=True)
class Artifact:
    """Immutable large payload reference belonging to a Run."""

    id: ArtifactId
    run_id: RunId
    kind: ArtifactKind
    storage_key: str
    content_type: str
    size_bytes: int
    checksum: str
    created_at: datetime = field(default_factory=utc_now)
    produced_by_grader_version_id: GraderVersionId | None = None

    def __post_init__(self) -> None:
        if not self.storage_key.strip():
            raise InvariantViolation(
                "Artifact storage key must be non-empty",
                code="INVALID_ARTIFACT_STORAGE_KEY",
            )
        if self.size_bytes < 0:
            raise InvariantViolation(
                "Artifact size cannot be negative",
                code="INVALID_ARTIFACT_SIZE",
            )
        if not self.checksum.strip():
            raise InvariantViolation(
                "Artifact checksum must be non-empty",
                code="INVALID_ARTIFACT_CHECKSUM",
            )


@dataclass(frozen=True, slots=True)
class ExecutionEvent:
    """Append-only, strictly ordered fact about a Run's execution."""

    id: ExecutionEventId
    run_id: RunId
    sequence: int
    kind: ActionKind
    action: NormalizedAction
    occurred_at: datetime
    artifact_ids: tuple[ArtifactId, ...] = ()
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.sequence < 0:
            raise InvariantViolation(
                "Execution Event sequence must be >= 0",
                code="INVALID_EVENT_SEQUENCE",
            )
        if action_kind_of(self.action) != self.kind:
            raise InvariantViolation(
                "Execution Event kind must match its normalized action",
                code="EVENT_KIND_MISMATCH",
            )


@dataclass(frozen=True, slots=True)
class ScoreValue:
    """Measurement content — objective or rubric — without business coupling."""

    numeric: float | None = None
    categorical: str | None = None
    passed: bool | None = None
    detail: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.numeric is None and self.categorical is None and self.passed is None:
            raise InvariantViolation(
                "Score value must include at least one measurement",
                code="EMPTY_SCORE_VALUE",
            )


@dataclass(frozen=True, slots=True)
class Score:
    """Single graded output: exactly one Run × one Grader Version (Invariant 2)."""

    id: ScoreId
    run_id: RunId
    grader_id: GraderId
    grader_version_id: GraderVersionId
    value: ScoreValue
    created_at: datetime = field(default_factory=utc_now)
    explanation_artifact_id: ArtifactId | None = None


class SandboxStatus(StrEnum):
    PROVISIONING = "provisioning"
    READY = "ready"
    DESTROYED = "destroyed"


@dataclass(slots=True)
class Sandbox:
    """Ephemeral, single-Run execution environment (Invariant 11).

    Not persisted as its own table (Schema Design), but modeled in Domain so
    the Execution Engine concept can express provision/destroy invariants.
    """

    id: SandboxId
    run_id: RunId
    status: SandboxStatus = SandboxStatus.PROVISIONING
    provisioned_at: datetime | None = None
    destroyed_at: datetime | None = None

    def mark_ready(self, *, at: datetime | None = None) -> None:
        if self.status is not SandboxStatus.PROVISIONING:
            raise InvariantViolation(
                "Sandbox can only become ready from provisioning",
                code="INVALID_SANDBOX_TRANSITION",
            )
        self.status = SandboxStatus.READY
        self.provisioned_at = at or utc_now()

    def destroy(self, *, at: datetime | None = None) -> None:
        if self.status is SandboxStatus.DESTROYED:
            raise InvariantViolation(
                "Sandbox is already destroyed",
                code="SANDBOX_ALREADY_DESTROYED",
            )
        self.status = SandboxStatus.DESTROYED
        self.destroyed_at = at or utc_now()

    def assert_usable(self) -> None:
        if self.status is not SandboxStatus.READY:
            raise InvariantViolation(
                "Sandbox is not ready for agent execution",
                code="SANDBOX_NOT_READY",
                details={"status": self.status.value},
            )
