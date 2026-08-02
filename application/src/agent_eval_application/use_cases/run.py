"""Run creation, lifecycle advancement, and grading orchestration use cases."""

from __future__ import annotations

from agent_eval_domain.common.ids import (
    AdapterVersionId,
    AgentId,
    AgentVersionId,
    ArtifactId,
    CaseId,
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
    SuiteId,
    SuiteVersionId,
)
from agent_eval_domain.execution.entities import ArtifactKind, ScoreValue
from agent_eval_domain.execution.ndm_codec import action_from_payload, action_to_payload
from agent_eval_domain.execution.normalized_model import action_kind_of
from agent_eval_domain.execution.run_factory import RunCreationCommand, RunFactory

from agent_eval_application.commands.run import (
    CancelRunCommand,
    CompleteRunCommand,
    CreateRunCommand,
    FailRunCommand,
    RecordArtifactCommand,
    RecordExecutionEventCommand,
    RecordScoreCommand,
    StartGradingCommand,
    StartRunCommand,
)
from agent_eval_application.common.id_generator import IdGenerator
from agent_eval_application.common.validation import require_non_empty
from agent_eval_application.dto.run import (
    ArtifactDTO,
    ArtifactRecordDTO,
    ExecutionEventDTO,
    ExecutionEventRecordDTO,
    RunDTO,
    ScoreDTO,
)
from agent_eval_application.errors import ApplicationValidationError
from agent_eval_application.ports.authorization import AuthorizationPort
from agent_eval_application.ports.event_dispatcher import DomainEventDispatcher
from agent_eval_application.ports.idempotency import IdempotencyStore
from agent_eval_application.ports.run_queue import RunQueue
from agent_eval_application.ports.unit_of_work import UnitOfWork, UnitOfWorkFactory
from agent_eval_application.queries.queries import (
    GetRunArtifactsQuery,
    GetRunEventsQuery,
    GetRunQuery,
    GetRunScoresQuery,
    ListRunsByProjectQuery,
)
from agent_eval_application.use_cases.base import (
    collect_events,
    replay_or_begin,
    run_in_uow,
    store_idempotent_result,
    with_domain_errors,
)


def _refetch_run(uow_factory: UnitOfWorkFactory, run_id: str) -> RunDTO:
    with uow_factory() as uow:
        run = with_domain_errors(lambda: uow.runs.get(RunId(run_id)))
        return RunDTO.from_domain(run)


def _resolve_pins(
    uow: UnitOfWork, command: CreateRunCommand, *, run_id: RunId
) -> RunCreationCommand:
    """Load and assemble pinned versions for RunFactory."""
    project_id = ProjectId(require_non_empty(command.project_id, field="project_id"))
    project = uow.projects.get(project_id)
    if not project.is_active():
        raise ApplicationValidationError(
            "Cannot create Run on a deprecated Project",
            code="PROJECT_NOT_ACTIVE",
            details={"project_id": project_id.value},
        )

    case = uow.cases.get(CaseId(require_non_empty(command.case_id, field="case_id")))
    if case.project_id != project_id:
        raise ApplicationValidationError(
            "Case does not belong to the target Project",
            code="CASE_PROJECT_MISMATCH",
            details={
                "case_id": case.id.value,
                "project_id": project_id.value,
            },
        )
    case_version = case.get_version(
        CaseVersionId(
            require_non_empty(command.case_version_id, field="case_version_id")
        )
    )
    prompt_version = case.prompt.get_version(
        PromptVersionId(
            require_non_empty(command.prompt_version_id, field="prompt_version_id")
        )
    )

    agent = uow.agents.get(
        AgentId(require_non_empty(command.agent_id, field="agent_id"))
    )
    agent_version = agent.get_version(
        AgentVersionId(
            require_non_empty(command.agent_version_id, field="agent_version_id")
        )
    )
    if agent.adapter_id is None:
        raise ApplicationValidationError(
            "Agent has no connected Adapter",
            code="AGENT_MISSING_ADAPTER",
            details={"agent_id": agent.id.value},
        )
    adapter = uow.adapters.get(agent.adapter_id)
    adapter_version = adapter.get_version(
        AdapterVersionId(
            require_non_empty(command.adapter_version_id, field="adapter_version_id")
        )
    )

    grader_versions = []
    for grader_id_raw, grader_version_id_raw in command.grader_version_refs:
        grader = uow.graders.get(
            GraderId(require_non_empty(grader_id_raw, field="grader_id"))
        )
        grader_versions.append(
            grader.get_version(
                GraderVersionId(
                    require_non_empty(grader_version_id_raw, field="grader_version_id")
                )
            )
        )

    suite_version = None
    suite_project_id = None
    if command.suite_version_id is not None:
        if command.suite_id is None:
            raise ApplicationValidationError(
                "suite_id is required when pinning a suite_version_id",
                code="MISSING_SUITE_ID",
            )
        suite = uow.suites.get(
            SuiteId(require_non_empty(command.suite_id, field="suite_id"))
        )
        suite_version = suite.get_version(
            SuiteVersionId(
                require_non_empty(command.suite_version_id, field="suite_version_id")
            )
        )
        suite_project_id = suite.project_id

    return RunCreationCommand(
        run_id=run_id,
        project_id=project_id,
        case_version=case_version,
        case_project_id=case.project_id,
        prompt_version=prompt_version,
        agent_version=agent_version,
        adapter_version=adapter_version,
        grader_versions=tuple(grader_versions),
        platform_version_id=PlatformVersionId(
            require_non_empty(command.platform_version_id, field="platform_version_id")
        ),
        suite_version=suite_version,
        suite_project_id=suite_project_id,
    )


class CreateRun:
    """Authorize → resolve pins → Domain RunFactory → persist → queue → enqueue.

    Returns once the Run is Queued — never after execution (ADR-0001).
    """

    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        ids: IdGenerator,
        auth: AuthorizationPort,
        events: DomainEventDispatcher,
        run_queue: RunQueue,
        idempotency: IdempotencyStore | None = None,
        run_factory: RunFactory | None = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._ids = ids
        self._auth = auth
        self._events = events
        self._run_queue = run_queue
        self._idempotency = idempotency
        self._run_factory = run_factory or RunFactory()

    def execute(self, command: CreateRunCommand) -> RunDTO:
        project_id = ProjectId(
            require_non_empty(command.project_id, field="project_id")
        )
        self._auth.ensure_can_manage_project(command.actor, project_id)

        if not command.grader_version_refs:
            raise ApplicationValidationError(
                "At least one grader version must be pinned",
                code="NO_GRADERS_PINNED",
            )

        replayed = replay_or_begin(
            self._idempotency,
            key=command.idempotency_key,
            scope=f"create_run:{project_id.value}",
            actor=command.actor,
            rebuild=lambda p: _refetch_run(self._uow_factory, p["id"]),
        )
        if replayed is not None:
            return replayed

        run_id = RunId(self._ids.new_id())

        def work(uow):
            creation = with_domain_errors(
                lambda: _resolve_pins(uow, command, run_id=run_id)
            )
            run = with_domain_errors(lambda: self._run_factory.create(creation))
            with_domain_errors(run.queue)
            uow.runs.save(run)
            # Enqueue after Domain transition to Queued. Infrastructure may
            # implement this via transactional outbox behind the port.
            self._run_queue.enqueue_run(run.id)
            return RunDTO.from_domain(run), collect_events(run)

        result = run_in_uow(self._uow_factory, self._events, work)
        store_idempotent_result(
            self._idempotency,
            key=command.idempotency_key,
            scope=f"create_run:{project_id.value}",
            actor=command.actor,
            result=result,
        )
        return result


class StartRun:
    """Worker advances Queued → Running."""

    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        auth: AuthorizationPort,
        events: DomainEventDispatcher,
    ) -> None:
        self._uow_factory = uow_factory
        self._auth = auth
        self._events = events

    def execute(self, command: StartRunCommand) -> RunDTO:
        run_id = RunId(require_non_empty(command.run_id, field="run_id"))
        sandbox_id = SandboxId(
            require_non_empty(command.sandbox_id, field="sandbox_id")
        )

        def work(uow):
            run = uow.runs.get(run_id)
            self._auth.ensure_can_manage_project(command.actor, run.pins.project_id)
            with_domain_errors(lambda: run.start(sandbox_id=sandbox_id))
            uow.runs.save(run)
            return RunDTO.from_domain(run), collect_events(run)

        return run_in_uow(self._uow_factory, self._events, work)


class StartGrading:
    """Worker advances Running → Grading after successful execution."""

    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        auth: AuthorizationPort,
        events: DomainEventDispatcher,
    ) -> None:
        self._uow_factory = uow_factory
        self._auth = auth
        self._events = events

    def execute(self, command: StartGradingCommand) -> RunDTO:
        run_id = RunId(require_non_empty(command.run_id, field="run_id"))

        def work(uow):
            run = uow.runs.get(run_id)
            self._auth.ensure_can_manage_project(command.actor, run.pins.project_id)
            with_domain_errors(run.start_grading)
            uow.runs.save(run)
            return RunDTO.from_domain(run), collect_events(run)

        return run_in_uow(self._uow_factory, self._events, work)


class CompleteRun:
    """Terminal success — agent may still have low Scores (not a platform failure)."""

    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        auth: AuthorizationPort,
        events: DomainEventDispatcher,
    ) -> None:
        self._uow_factory = uow_factory
        self._auth = auth
        self._events = events

    def execute(self, command: CompleteRunCommand) -> RunDTO:
        run_id = RunId(require_non_empty(command.run_id, field="run_id"))

        def work(uow):
            run = uow.runs.get(run_id)
            self._auth.ensure_can_manage_project(command.actor, run.pins.project_id)
            with_domain_errors(run.complete)
            uow.runs.save(run)
            return RunDTO.from_domain(run), collect_events(run)

        return run_in_uow(self._uow_factory, self._events, work)


class FailRun:
    """Platform-caused terminal failure (Backend Architecture §9)."""

    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        auth: AuthorizationPort,
        events: DomainEventDispatcher,
    ) -> None:
        self._uow_factory = uow_factory
        self._auth = auth
        self._events = events

    def execute(self, command: FailRunCommand) -> RunDTO:
        run_id = RunId(require_non_empty(command.run_id, field="run_id"))
        reason = require_non_empty(command.reason, field="reason")

        def work(uow):
            run = uow.runs.get(run_id)
            self._auth.ensure_can_manage_project(command.actor, run.pins.project_id)
            with_domain_errors(lambda: run.fail(reason=reason))
            uow.runs.save(run)
            return RunDTO.from_domain(run), collect_events(run)

        return run_in_uow(self._uow_factory, self._events, work)


class CancelRun:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        auth: AuthorizationPort,
        events: DomainEventDispatcher,
    ) -> None:
        self._uow_factory = uow_factory
        self._auth = auth
        self._events = events

    def execute(self, command: CancelRunCommand) -> RunDTO:
        run_id = RunId(require_non_empty(command.run_id, field="run_id"))

        def work(uow):
            run = uow.runs.get(run_id)
            self._auth.ensure_can_manage_project(command.actor, run.pins.project_id)
            with_domain_errors(lambda: run.cancel(reason=command.reason))
            uow.runs.save(run)
            return RunDTO.from_domain(run), collect_events(run)

        return run_in_uow(self._uow_factory, self._events, work)


class RecordScore:
    """Persist a Score from the Grader Layer through Application (never direct DB)."""

    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        ids: IdGenerator,
        auth: AuthorizationPort,
        events: DomainEventDispatcher,
    ) -> None:
        self._uow_factory = uow_factory
        self._ids = ids
        self._auth = auth
        self._events = events

    def execute(self, command: RecordScoreCommand) -> RunDTO:
        run_id = RunId(require_non_empty(command.run_id, field="run_id"))

        def work(uow):
            run = uow.runs.get(run_id)
            self._auth.ensure_can_manage_project(command.actor, run.pins.project_id)
            value = ScoreValue(
                numeric=command.numeric,
                categorical=command.categorical,
                passed=command.passed,
                detail=dict(command.detail),
            )
            explanation = (
                ArtifactId(command.explanation_artifact_id)
                if command.explanation_artifact_id
                else None
            )
            with_domain_errors(
                lambda: run.record_score(
                    score_id=ScoreId(self._ids.new_id()),
                    grader_id=GraderId(
                        require_non_empty(command.grader_id, field="grader_id")
                    ),
                    grader_version_id=GraderVersionId(
                        require_non_empty(
                            command.grader_version_id, field="grader_version_id"
                        )
                    ),
                    value=value,
                    explanation_artifact_id=explanation,
                )
            )
            uow.runs.save(run)
            return RunDTO.from_domain(run), collect_events(run)

        return run_in_uow(self._uow_factory, self._events, work)


class RecordArtifact:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        ids: IdGenerator,
        auth: AuthorizationPort,
        events: DomainEventDispatcher,
    ) -> None:
        self._uow_factory = uow_factory
        self._ids = ids
        self._auth = auth
        self._events = events

    def execute(self, command: RecordArtifactCommand) -> ArtifactRecordDTO:
        run_id = RunId(require_non_empty(command.run_id, field="run_id"))
        try:
            kind = ArtifactKind(require_non_empty(command.kind, field="kind"))
        except ValueError as exc:
            raise ApplicationValidationError(
                f"Unknown artifact kind: {command.kind}",
                code="INVALID_ARTIFACT_KIND",
                details={"kind": command.kind},
                cause=exc,
            ) from exc

        artifact_id = ArtifactId(
            require_non_empty(command.artifact_id, field="artifact_id")
            if command.artifact_id
            else self._ids.new_id()
        )

        def work(uow):
            run = uow.runs.get(run_id)
            self._auth.ensure_can_manage_project(command.actor, run.pins.project_id)
            produced_by = (
                GraderVersionId(command.produced_by_grader_version_id)
                if command.produced_by_grader_version_id
                else None
            )
            before_ids = {a.id.value for a in run.artifacts}
            artifact = with_domain_errors(
                lambda: run.store_artifact(
                    artifact_id=artifact_id,
                    kind=kind,
                    storage_key=require_non_empty(
                        command.storage_key, field="storage_key"
                    ),
                    content_type=require_non_empty(
                        command.content_type, field="content_type"
                    ),
                    size_bytes=command.size_bytes,
                    checksum=require_non_empty(command.checksum, field="checksum"),
                    produced_by_grader_version_id=produced_by,
                )
            )
            already = artifact.id.value in before_ids
            uow.runs.save(run)
            dto = ArtifactRecordDTO(
                id=artifact.id.value,
                run_id=run.id.value,
                kind=artifact.kind.value,
                storage_key=artifact.storage_key,
                content_type=artifact.content_type,
                size_bytes=artifact.size_bytes,
                checksum=artifact.checksum,
                already_recorded=already,
            )
            return dto, collect_events(run)

        return run_in_uow(self._uow_factory, self._events, work)


class RecordExecutionEvent:
    """Persist one append-only Execution Event through the Application Layer."""

    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        auth: AuthorizationPort,
        events: DomainEventDispatcher,
    ) -> None:
        self._uow_factory = uow_factory
        self._auth = auth
        self._events = events

    def execute(self, command: RecordExecutionEventCommand) -> ExecutionEventRecordDTO:
        run_id = RunId(require_non_empty(command.run_id, field="run_id"))
        event_id = ExecutionEventId(
            require_non_empty(command.execution_event_id, field="execution_event_id")
        )
        try:
            action = action_from_payload(dict(command.action))
        except (KeyError, ValueError, TypeError) as exc:
            raise ApplicationValidationError(
                "Invalid Normalized Domain Model action payload",
                code="INVALID_ACTION_PAYLOAD",
                details={"error": str(exc)},
                cause=exc,
            ) from exc

        def work(uow):
            run = uow.runs.get(run_id)
            self._auth.ensure_can_manage_project(command.actor, run.pins.project_id)
            before_ids = {e.id.value for e in run.execution_events}
            event = with_domain_errors(
                lambda: run.record_execution_event(
                    event_id=event_id,
                    action=action,
                    occurred_at=command.occurred_at,
                    artifact_ids=[
                        ArtifactId(require_non_empty(a, field="artifact_id"))
                        for a in command.artifact_ids
                    ],
                    metadata=dict(command.metadata),
                )
            )
            already = event.id.value in before_ids
            uow.runs.save(run)
            dto = ExecutionEventRecordDTO(
                id=event.id.value,
                run_id=run.id.value,
                sequence=event.sequence,
                kind=action_kind_of(event.action).value,
                artifact_ids=tuple(a.value for a in event.artifact_ids),
                occurred_at=event.occurred_at,
                already_recorded=already,
            )
            return dto, collect_events(run)

        return run_in_uow(self._uow_factory, self._events, work)


class GetRun:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        auth: AuthorizationPort,
    ) -> None:
        self._uow_factory = uow_factory
        self._auth = auth

    def execute(self, query: GetRunQuery) -> RunDTO:
        run_id = RunId(require_non_empty(query.run_id, field="run_id"))
        with self._uow_factory() as uow:
            run = with_domain_errors(lambda: uow.runs.get(run_id))
            self._auth.ensure_can_access_project(query.actor, run.pins.project_id)
            return RunDTO.from_domain(run)


class ListRunsByProject:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        auth: AuthorizationPort,
    ) -> None:
        self._uow_factory = uow_factory
        self._auth = auth

    def execute(self, query: ListRunsByProjectQuery) -> list[RunDTO]:
        project_id = ProjectId(require_non_empty(query.project_id, field="project_id"))
        self._auth.ensure_can_access_project(query.actor, project_id)
        with self._uow_factory() as uow:
            runs = with_domain_errors(lambda: uow.runs.list_by_project(project_id))
            return [RunDTO.from_domain(r) for r in runs]


class GetRunEvents:
    """Return ordered Execution Events for a Run (owned nested read)."""

    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        auth: AuthorizationPort,
    ) -> None:
        self._uow_factory = uow_factory
        self._auth = auth

    def execute(self, query: GetRunEventsQuery) -> list[ExecutionEventDTO]:
        run_id = RunId(require_non_empty(query.run_id, field="run_id"))
        with self._uow_factory() as uow:
            run = with_domain_errors(lambda: uow.runs.get(run_id))
            self._auth.ensure_can_access_project(query.actor, run.pins.project_id)
            return [
                ExecutionEventDTO(
                    id=event.id.value,
                    run_id=run.id.value,
                    sequence=event.sequence,
                    kind=event.kind.value,
                    action=action_to_payload(event.action),
                    artifact_ids=tuple(a.value for a in event.artifact_ids),
                    occurred_at=event.occurred_at,
                    metadata=dict(event.metadata),
                )
                for event in run.execution_events
            ]


class GetRunArtifacts:
    """Return Artifact metadata for a Run (owned nested read)."""

    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        auth: AuthorizationPort,
    ) -> None:
        self._uow_factory = uow_factory
        self._auth = auth

    def execute(self, query: GetRunArtifactsQuery) -> list[ArtifactDTO]:
        run_id = RunId(require_non_empty(query.run_id, field="run_id"))
        with self._uow_factory() as uow:
            run = with_domain_errors(lambda: uow.runs.get(run_id))
            self._auth.ensure_can_access_project(query.actor, run.pins.project_id)
            return [
                ArtifactDTO(
                    id=artifact.id.value,
                    run_id=run.id.value,
                    kind=artifact.kind.value,
                    storage_key=artifact.storage_key,
                    content_type=artifact.content_type,
                    size_bytes=artifact.size_bytes,
                    checksum=artifact.checksum,
                    created_at=artifact.created_at,
                    produced_by_grader_version_id=(
                        artifact.produced_by_grader_version_id.value
                        if artifact.produced_by_grader_version_id
                        else None
                    ),
                )
                for artifact in run.artifacts
            ]


class GetRunScores:
    """Return Scores for a Run (owned nested read)."""

    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        auth: AuthorizationPort,
    ) -> None:
        self._uow_factory = uow_factory
        self._auth = auth

    def execute(self, query: GetRunScoresQuery) -> list[ScoreDTO]:
        run_id = RunId(require_non_empty(query.run_id, field="run_id"))
        with self._uow_factory() as uow:
            run = with_domain_errors(lambda: uow.runs.get(run_id))
            self._auth.ensure_can_access_project(query.actor, run.pins.project_id)
            dto = RunDTO.from_domain(run)
            return list(dto.scores)
