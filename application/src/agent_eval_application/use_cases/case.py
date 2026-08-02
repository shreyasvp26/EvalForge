"""Case and Prompt use cases."""

from __future__ import annotations

from agent_eval_domain.common.ids import (
    CaseId,
    CaseVersionId,
    GraderId,
    ProjectId,
    PromptId,
    PromptVersionId,
)
from agent_eval_domain.evaluation_management.case import (
    EvaluationCase,
    ReferenceRepositoryState,
)

from agent_eval_application.commands.case import (
    CreateCaseCommand,
    CreateCaseDraftVersionCommand,
    CreatePromptDraftVersionCommand,
    DeprecateCaseCommand,
    PublishCaseVersionCommand,
    PublishPromptVersionCommand,
)
from agent_eval_application.common.id_generator import IdGenerator
from agent_eval_application.common.validation import require_non_empty
from agent_eval_application.dto.case import CaseDTO, CaseVersionDTO, PromptVersionDTO
from agent_eval_application.errors import ApplicationValidationError
from agent_eval_application.ports.authorization import AuthorizationPort
from agent_eval_application.ports.event_dispatcher import DomainEventDispatcher
from agent_eval_application.ports.idempotency import IdempotencyStore
from agent_eval_application.ports.unit_of_work import UnitOfWorkFactory
from agent_eval_application.queries.queries import GetCaseQuery, ListCasesByProjectQuery
from agent_eval_application.use_cases.base import (
    collect_events,
    replay_or_begin,
    run_in_uow,
    store_idempotent_result,
    with_domain_errors,
)


def _refetch_case(uow_factory: UnitOfWorkFactory, case_id: str) -> CaseDTO:
    with uow_factory() as uow:
        case = with_domain_errors(lambda: uow.cases.get(CaseId(case_id)))
        return CaseDTO.from_domain(case)


class CreateCase:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        ids: IdGenerator,
        auth: AuthorizationPort,
        events: DomainEventDispatcher,
        idempotency: IdempotencyStore | None = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._ids = ids
        self._auth = auth
        self._events = events
        self._idempotency = idempotency

    def execute(self, command: CreateCaseCommand) -> CaseDTO:
        name = require_non_empty(command.name, field="name")
        project_id = ProjectId(
            require_non_empty(command.project_id, field="project_id")
        )
        self._auth.ensure_can_manage_project(command.actor, project_id)

        replayed = replay_or_begin(
            self._idempotency,
            key=command.idempotency_key,
            scope=f"create_case:{project_id.value}",
            actor=command.actor,
            rebuild=lambda p: _refetch_case(self._uow_factory, p["id"]),
        )
        if replayed is not None:
            return replayed

        case_id = CaseId(self._ids.new_id())
        prompt_id = PromptId(self._ids.new_id())

        def work(uow):
            project = uow.projects.get(project_id)
            if not project.is_active():
                raise ApplicationValidationError(
                    "Cannot create Case on a deprecated Project",
                    code="PROJECT_NOT_ACTIVE",
                    details={"project_id": project_id.value},
                )
            case = with_domain_errors(
                lambda: EvaluationCase.create(
                    case_id=case_id,
                    project_id=project_id,
                    prompt_id=prompt_id,
                    name=name,
                    description=command.description,
                )
            )
            uow.cases.save(case)
            return CaseDTO.from_domain(case), collect_events(case)

        result = run_in_uow(self._uow_factory, self._events, work)
        store_idempotent_result(
            self._idempotency,
            key=command.idempotency_key,
            scope=f"create_case:{project_id.value}",
            actor=command.actor,
            result=result,
        )
        return result


class CreatePromptDraftVersion:
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

    def execute(self, command: CreatePromptDraftVersionCommand) -> PromptVersionDTO:
        case_id = CaseId(require_non_empty(command.case_id, field="case_id"))
        content = require_non_empty(command.content, field="content")

        def work(uow):
            case = uow.cases.get(case_id)
            self._auth.ensure_can_manage_project(command.actor, case.project_id)
            version = with_domain_errors(
                lambda: case.prompt.create_draft_version(
                    version_id=PromptVersionId(self._ids.new_id()),
                    content=content,
                )
            )
            uow.cases.save(case)
            return PromptVersionDTO.from_domain(version), collect_events(case)

        return run_in_uow(self._uow_factory, self._events, work)


class PublishPromptVersion:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        auth: AuthorizationPort,
        events: DomainEventDispatcher,
    ) -> None:
        self._uow_factory = uow_factory
        self._auth = auth
        self._events = events

    def execute(self, command: PublishPromptVersionCommand) -> PromptVersionDTO:
        case_id = CaseId(require_non_empty(command.case_id, field="case_id"))
        version_id = PromptVersionId(
            require_non_empty(command.version_id, field="version_id")
        )

        def work(uow):
            case = uow.cases.get(case_id)
            self._auth.ensure_can_manage_project(command.actor, case.project_id)
            version = with_domain_errors(
                lambda: case.prompt.publish_version(version_id)
            )
            uow.cases.save(case)
            return PromptVersionDTO.from_domain(version), collect_events(case)

        return run_in_uow(self._uow_factory, self._events, work)


class CreateCaseDraftVersion:
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

    def execute(self, command: CreateCaseDraftVersionCommand) -> CaseVersionDTO:
        case_id = CaseId(require_non_empty(command.case_id, field="case_id"))

        def work(uow):
            case = uow.cases.get(case_id)
            self._auth.ensure_can_manage_project(command.actor, case.project_id)
            version = with_domain_errors(
                lambda: case.create_draft_version(
                    version_id=CaseVersionId(self._ids.new_id()),
                    description=require_non_empty(
                        command.description, field="description"
                    ),
                    reference_repository=ReferenceRepositoryState(
                        repository_url=require_non_empty(
                            command.repository_url, field="repository_url"
                        ),
                        commit_sha=require_non_empty(
                            command.commit_sha, field="commit_sha"
                        ),
                        subdirectory=command.subdirectory,
                    ),
                    expected_checks=list(command.expected_checks),
                    applicable_grader_ids=[
                        GraderId(require_non_empty(g, field="grader_id"))
                        for g in command.applicable_grader_ids
                    ],
                    prompt_version_id=PromptVersionId(
                        require_non_empty(
                            command.prompt_version_id, field="prompt_version_id"
                        )
                    ),
                )
            )
            uow.cases.save(case)
            return CaseVersionDTO.from_domain(version), collect_events(case)

        return run_in_uow(self._uow_factory, self._events, work)


class PublishCaseVersion:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        auth: AuthorizationPort,
        events: DomainEventDispatcher,
    ) -> None:
        self._uow_factory = uow_factory
        self._auth = auth
        self._events = events

    def execute(self, command: PublishCaseVersionCommand) -> CaseVersionDTO:
        case_id = CaseId(require_non_empty(command.case_id, field="case_id"))
        version_id = CaseVersionId(
            require_non_empty(command.version_id, field="version_id")
        )

        def work(uow):
            case = uow.cases.get(case_id)
            self._auth.ensure_can_manage_project(command.actor, case.project_id)
            version = with_domain_errors(lambda: case.publish_version(version_id))
            uow.cases.save(case)
            return CaseVersionDTO.from_domain(version), collect_events(case)

        return run_in_uow(self._uow_factory, self._events, work)


class DeprecateCase:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        auth: AuthorizationPort,
        events: DomainEventDispatcher,
    ) -> None:
        self._uow_factory = uow_factory
        self._auth = auth
        self._events = events

    def execute(self, command: DeprecateCaseCommand) -> CaseDTO:
        case_id = CaseId(require_non_empty(command.case_id, field="case_id"))

        def work(uow):
            case = uow.cases.get(case_id)
            self._auth.ensure_can_manage_project(command.actor, case.project_id)
            with_domain_errors(case.deprecate)
            uow.cases.save(case)
            return CaseDTO.from_domain(case), collect_events(case)

        return run_in_uow(self._uow_factory, self._events, work)


class GetCase:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        auth: AuthorizationPort,
    ) -> None:
        self._uow_factory = uow_factory
        self._auth = auth

    def execute(self, query: GetCaseQuery) -> CaseDTO:
        case_id = CaseId(require_non_empty(query.case_id, field="case_id"))
        with self._uow_factory() as uow:
            case = with_domain_errors(lambda: uow.cases.get(case_id))
            self._auth.ensure_can_access_project(query.actor, case.project_id)
            return CaseDTO.from_domain(case)


class ListCasesByProject:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        auth: AuthorizationPort,
    ) -> None:
        self._uow_factory = uow_factory
        self._auth = auth

    def execute(self, query: ListCasesByProjectQuery) -> list[CaseDTO]:
        project_id = ProjectId(require_non_empty(query.project_id, field="project_id"))
        self._auth.ensure_can_access_project(query.actor, project_id)
        with self._uow_factory() as uow:
            cases = with_domain_errors(lambda: uow.cases.list_by_project(project_id))
            return [CaseDTO.from_domain(c) for c in cases]
