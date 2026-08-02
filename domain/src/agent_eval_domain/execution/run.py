"""Evaluation Run aggregate root — central unit of evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from agent_eval_domain.common.aggregate import AggregateRoot
from agent_eval_domain.common.errors import InvariantViolation
from agent_eval_domain.common.events import utc_now
from agent_eval_domain.common.ids import (
    AdapterVersionId,
    AgentVersionId,
    ArtifactId,
    CaseVersionId,
    ExecutionEventId,
    GraderId,
    GraderVersionId,
    PlatformVersionId,
    ProjectId,
    PromptVersionId,
    RunId,
    SandboxId,
    ScoreId,
    SuiteVersionId,
)
from agent_eval_domain.execution.entities import (
    Artifact,
    ArtifactKind,
    ExecutionCost,
    ExecutionEvent,
    Sandbox,
    SandboxStatus,
    Score,
    ScoreValue,
)
from agent_eval_domain.execution.events import (
    ArtifactStored,
    ExecutionEventRecorded,
    RunCancelled,
    RunCompleted,
    RunCreated,
    RunFailed,
    RunGradingStarted,
    RunQueued,
    RunStarted,
    ScoreProduced,
)
from agent_eval_domain.execution.normalized_model import (
    NormalizedAction,
    action_kind_of,
)
from agent_eval_domain.execution.run_status import (
    RunStatus,
    assert_run_transition,
    is_terminal,
)


@dataclass(frozen=True, slots=True)
class RunPins:
    """All seven versioning axes pinned at Run creation (Domain Model §9)."""

    project_id: ProjectId
    case_version_id: CaseVersionId
    prompt_version_id: PromptVersionId
    agent_version_id: AgentVersionId
    adapter_version_id: AdapterVersionId
    platform_version_id: PlatformVersionId
    grader_version_ids: tuple[GraderVersionId, ...]
    suite_version_id: SuiteVersionId | None = None

    def __post_init__(self) -> None:
        if len(self.grader_version_ids) != len(set(self.grader_version_ids)):
            raise InvariantViolation(
                "Pinned Grader Versions must be unique",
                code="DUPLICATE_PINNED_GRADER",
            )


@dataclass(slots=True)
class EvaluationRun(AggregateRoot):
    """Immutable identity + pinned versions; append-only history; finite lifecycle."""

    id: RunId
    pins: RunPins
    status: RunStatus = RunStatus.CREATED
    created_at: datetime = field(default_factory=utc_now)
    cost: ExecutionCost | None = None
    failure_reason: str | None = None
    cancellation_reason: str | None = None
    sandbox: Sandbox | None = None
    _execution_events: list[ExecutionEvent] = field(default_factory=list, repr=False)
    _artifacts: list[Artifact] = field(default_factory=list, repr=False)
    _scores: list[Score] = field(default_factory=list, repr=False)
    _next_sequence: int = field(default=0, repr=False)

    def __post_init__(self) -> None:
        AggregateRoot.__init__(self)

    @classmethod
    def create(cls, *, run_id: RunId, pins: RunPins) -> EvaluationRun:
        run = cls(id=run_id, pins=pins)
        run._record(
            RunCreated(
                run_id=run_id,
                project_id=pins.project_id.value,
                case_version_id=pins.case_version_id.value,
                prompt_version_id=pins.prompt_version_id.value,
                agent_version_id=pins.agent_version_id.value,
                adapter_version_id=pins.adapter_version_id.value,
                suite_version_id=(
                    pins.suite_version_id.value if pins.suite_version_id else None
                ),
                platform_version_id=pins.platform_version_id.value,
                grader_version_ids=tuple(g.value for g in pins.grader_version_ids),
            )
        )
        return run

    # --- read accessors -------------------------------------------------

    @property
    def execution_events(self) -> tuple[ExecutionEvent, ...]:
        return tuple(self._execution_events)

    @property
    def artifacts(self) -> tuple[Artifact, ...]:
        return tuple(self._artifacts)

    @property
    def scores(self) -> tuple[Score, ...]:
        return tuple(self._scores)

    @property
    def expected_grader_count(self) -> int:
        return len(self.pins.grader_version_ids)

    @property
    def is_partially_graded(self) -> bool:
        return (
            self.status is RunStatus.COMPLETED
            and len(self._scores) < self.expected_grader_count
        )

    def is_terminal(self) -> bool:
        return is_terminal(self.status)

    # --- lifecycle transitions ------------------------------------------

    def queue(self) -> None:
        self._transition_to(RunStatus.QUEUED)
        self._record(RunQueued(run_id=self.id))

    def start(self, *, sandbox_id: SandboxId) -> Sandbox:
        self._transition_to(RunStatus.RUNNING)
        sandbox = Sandbox(id=sandbox_id, run_id=self.id)
        sandbox.mark_ready()
        self.sandbox = sandbox
        self._record(RunStarted(run_id=self.id, sandbox_id=sandbox_id.value))
        return sandbox

    def start_grading(self) -> None:
        self._destroy_sandbox_if_present()
        self._transition_to(RunStatus.GRADING)
        self._record(RunGradingStarted(run_id=self.id))

    def complete(self) -> None:
        self._transition_to(RunStatus.COMPLETED)
        self._record(
            RunCompleted(
                run_id=self.id,
                expected_grader_count=self.expected_grader_count,
                produced_score_count=len(self._scores),
                is_partially_graded=len(self._scores) < self.expected_grader_count,
            )
        )

    def fail(self, *, reason: str) -> None:
        if not reason.strip():
            raise InvariantViolation(
                "Failure reason must be non-empty",
                code="INVALID_FAILURE_REASON",
            )
        self._destroy_sandbox_if_present()
        self._transition_to(RunStatus.FAILED)
        self.failure_reason = reason.strip()
        self._record(RunFailed(run_id=self.id, reason=self.failure_reason))

    def cancel(self, *, reason: str | None = None) -> None:
        self._destroy_sandbox_if_present()
        self._transition_to(RunStatus.CANCELLED)
        self.cancellation_reason = reason.strip() if reason else None
        self._record(RunCancelled(run_id=self.id, reason=self.cancellation_reason))

    # --- append-only writes ---------------------------------------------

    def record_execution_event(
        self,
        *,
        event_id: ExecutionEventId,
        action: NormalizedAction,
        occurred_at: datetime | None = None,
        artifact_ids: list[ArtifactId] | None = None,
        metadata: dict[str, str] | None = None,
    ) -> ExecutionEvent:
        self._assert_accepts_execution_events()
        if self.sandbox is not None:
            self.sandbox.assert_usable()
        refs = tuple(artifact_ids or ())
        for artifact_id in refs:
            if not any(a.id == artifact_id for a in self._artifacts):
                raise InvariantViolation(
                    "Execution Event cannot reference an unknown Artifact",
                    code="UNKNOWN_ARTIFACT_REF",
                    details={"artifact_id": artifact_id.value},
                )
        event = ExecutionEvent(
            id=event_id,
            run_id=self.id,
            sequence=self._next_sequence,
            kind=action_kind_of(action),
            action=action,
            occurred_at=occurred_at or utc_now(),
            artifact_ids=refs,
            metadata=dict(metadata or {}),
        )
        self._execution_events.append(event)
        self._next_sequence += 1
        self._record(
            ExecutionEventRecorded(
                run_id=self.id,
                execution_event_id=event_id,
                sequence=event.sequence,
            )
        )
        return event

    def store_artifact(
        self,
        *,
        artifact_id: ArtifactId,
        kind: ArtifactKind,
        storage_key: str,
        content_type: str,
        size_bytes: int,
        checksum: str,
        produced_by_grader_version_id: GraderVersionId | None = None,
        created_at: datetime | None = None,
    ) -> Artifact:
        if self.is_terminal():
            raise InvariantViolation(
                "Cannot store Artifacts on a terminal Run",
                code="RUN_TERMINAL",
                details={"status": self.status.value},
            )
        if self.status not in {RunStatus.RUNNING, RunStatus.GRADING}:
            raise InvariantViolation(
                "Artifacts may only be stored while Running or Grading",
                code="INVALID_ARTIFACT_PHASE",
                details={"status": self.status.value},
            )
        if produced_by_grader_version_id is not None:
            if self.status is not RunStatus.GRADING:
                raise InvariantViolation(
                    "Grader-produced Artifacts require Grading state",
                    code="GRADER_ARTIFACT_WRONG_PHASE",
                )
            if produced_by_grader_version_id not in self.pins.grader_version_ids:
                raise InvariantViolation(
                    "Artifact Grader Version is not pinned on this Run",
                    code="UNPINNED_GRADER_ARTIFACT",
                )
        artifact = Artifact(
            id=artifact_id,
            run_id=self.id,
            kind=kind,
            storage_key=storage_key,
            content_type=content_type,
            size_bytes=size_bytes,
            checksum=checksum,
            created_at=created_at or utc_now(),
            produced_by_grader_version_id=produced_by_grader_version_id,
        )
        self._artifacts.append(artifact)
        self._record(ArtifactStored(run_id=self.id, artifact_id=artifact_id))
        return artifact

    def record_score(
        self,
        *,
        score_id: ScoreId,
        grader_id: GraderId,
        grader_version_id: GraderVersionId,
        value: ScoreValue,
        explanation_artifact_id: ArtifactId | None = None,
        created_at: datetime | None = None,
    ) -> Score:
        if self.status is not RunStatus.GRADING:
            raise InvariantViolation(
                "Scores may only be recorded while Grading",
                code="SCORE_WRONG_PHASE",
                details={"status": self.status.value},
            )
        if grader_version_id not in self.pins.grader_version_ids:
            raise InvariantViolation(
                "Score Grader Version is not pinned on this Run",
                code="UNPINNED_GRADER_SCORE",
                details={"grader_version_id": grader_version_id.value},
            )
        if any(s.grader_version_id == grader_version_id for s in self._scores):
            raise InvariantViolation(
                "A Run may have at most one Score per Grader Version",
                code="DUPLICATE_SCORE",
                details={"grader_version_id": grader_version_id.value},
            )
        if explanation_artifact_id is not None:
            if not any(a.id == explanation_artifact_id for a in self._artifacts):
                raise InvariantViolation(
                    "Score explanation Artifact must belong to this Run",
                    code="UNKNOWN_SCORE_ARTIFACT",
                )
        score = Score(
            id=score_id,
            run_id=self.id,
            grader_id=grader_id,
            grader_version_id=grader_version_id,
            value=value,
            created_at=created_at or utc_now(),
            explanation_artifact_id=explanation_artifact_id,
        )
        self._scores.append(score)
        self._record(
            ScoreProduced(
                run_id=self.id,
                score_id=score_id,
                grader_version_id=grader_version_id,
            )
        )
        return score

    def record_cost(self, cost: ExecutionCost) -> None:
        if self.cost is not None:
            raise InvariantViolation(
                "Run cost facts are immutable once written",
                code="COST_ALREADY_RECORDED",
            )
        if self.status not in {RunStatus.RUNNING, RunStatus.GRADING}:
            raise InvariantViolation(
                "Cost may only be recorded during or immediately after execution",
                code="COST_WRONG_PHASE",
                details={"status": self.status.value},
            )
        self.cost = cost

    # --- internals ------------------------------------------------------

    def _transition_to(self, target: RunStatus) -> None:
        if self.is_terminal():
            raise InvariantViolation(
                "Terminal Runs are permanently closed",
                code="RUN_TERMINAL",
                details={"status": self.status.value, "attempted": target.value},
            )
        assert_run_transition(current=self.status, target=target)
        self.status = target

    def _assert_accepts_execution_events(self) -> None:
        if self.status is not RunStatus.RUNNING:
            raise InvariantViolation(
                "Execution Events may only be recorded while Running",
                code="EVENT_WRONG_PHASE",
                details={"status": self.status.value},
            )

    def _destroy_sandbox_if_present(self) -> None:
        if (
            self.sandbox is not None
            and self.sandbox.status is not SandboxStatus.DESTROYED
        ):
            self.sandbox.destroy()
