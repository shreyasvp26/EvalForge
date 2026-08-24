"""Project use cases."""

from __future__ import annotations

from datetime import datetime

from agent_eval_domain.common.ids import ProjectId
from agent_eval_domain.evaluation_management.project import Project

from agent_eval_application.commands.project import (
    CreateProjectCommand,
    DeprecateProjectCommand,
    RenameProjectCommand,
    UpdateProjectSettingsCommand,
)
from agent_eval_application.common.id_generator import IdGenerator
from agent_eval_application.common.validation import require_non_empty
from agent_eval_application.dto.project import ProjectDTO
from agent_eval_application.errors import AuthorizationError
from agent_eval_application.ports.authorization import AuthorizationPort
from agent_eval_application.ports.event_dispatcher import DomainEventDispatcher
from agent_eval_application.ports.idempotency import IdempotencyStore
from agent_eval_application.ports.unit_of_work import UnitOfWorkFactory
from agent_eval_application.queries.queries import GetProjectQuery, ListProjectsQuery
from agent_eval_application.use_cases.base import (
    collect_events,
    replay_or_begin,
    run_in_uow,
    store_idempotent_result,
    with_domain_errors,
)


def _rebuild_project(payload: dict) -> ProjectDTO:
    return ProjectDTO(
        id=payload["id"],
        name=payload["name"],
        description=payload["description"],
        status=payload["status"],
        created_at=(
            payload["created_at"]
            if isinstance(payload["created_at"], datetime)
            else datetime.fromisoformat(payload["created_at"])
        ),
        settings=dict(payload["settings"]),
    )


class CreateProject:
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

    def execute(self, command: CreateProjectCommand) -> ProjectDTO:
        name = require_non_empty(command.name, field="name")
        self._auth.ensure_can_create_project(command.actor)
        replayed = replay_or_begin(
            self._idempotency,
            key=command.idempotency_key,
            scope="create_project",
            actor=command.actor,
            rebuild=_rebuild_project,
        )
        if replayed is not None:
            return replayed

        project_id = ProjectId(self._ids.new_id())

        def work(uow):
            project = with_domain_errors(
                lambda: Project.create(
                    project_id=project_id,
                    name=name,
                    description=command.description,
                    settings=command.settings,
                )
            )
            uow.projects.save(project)
            # Owner membership is Application authorization state, not a Domain
            # concept — but it must commit atomically with the Project row.
            self._auth.grant_project_owner(command.actor, project_id)
            return ProjectDTO.from_domain(project), collect_events(project)

        result = run_in_uow(self._uow_factory, self._events, work)
        store_idempotent_result(
            self._idempotency,
            key=command.idempotency_key,
            scope="create_project",
            actor=command.actor,
            result=result,
        )
        return result


class RenameProject:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        auth: AuthorizationPort,
        events: DomainEventDispatcher,
    ) -> None:
        self._uow_factory = uow_factory
        self._auth = auth
        self._events = events

    def execute(self, command: RenameProjectCommand) -> ProjectDTO:
        name = require_non_empty(command.name, field="name")
        project_id = ProjectId(
            require_non_empty(command.project_id, field="project_id")
        )
        self._auth.ensure_can_manage_project(command.actor, project_id)

        def work(uow):
            project = uow.projects.get(project_id)
            with_domain_errors(lambda: project.rename(name))
            uow.projects.save(project)
            return ProjectDTO.from_domain(project), collect_events(project)

        return run_in_uow(self._uow_factory, self._events, work)


class UpdateProjectSettings:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        auth: AuthorizationPort,
        events: DomainEventDispatcher,
    ) -> None:
        self._uow_factory = uow_factory
        self._auth = auth
        self._events = events

    def execute(self, command: UpdateProjectSettingsCommand) -> ProjectDTO:
        project_id = ProjectId(
            require_non_empty(command.project_id, field="project_id")
        )
        self._auth.ensure_can_manage_project(command.actor, project_id)

        def work(uow):
            project = uow.projects.get(project_id)
            with_domain_errors(lambda: project.update_settings(command.settings))
            uow.projects.save(project)
            return ProjectDTO.from_domain(project), collect_events(project)

        return run_in_uow(self._uow_factory, self._events, work)


class DeprecateProject:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        auth: AuthorizationPort,
        events: DomainEventDispatcher,
    ) -> None:
        self._uow_factory = uow_factory
        self._auth = auth
        self._events = events

    def execute(self, command: DeprecateProjectCommand) -> ProjectDTO:
        project_id = ProjectId(
            require_non_empty(command.project_id, field="project_id")
        )
        self._auth.ensure_can_manage_project(command.actor, project_id)

        def work(uow):
            project = uow.projects.get(project_id)
            with_domain_errors(project.deprecate)
            uow.projects.save(project)
            return ProjectDTO.from_domain(project), collect_events(project)

        return run_in_uow(self._uow_factory, self._events, work)


class GetProject:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        auth: AuthorizationPort,
    ) -> None:
        self._uow_factory = uow_factory
        self._auth = auth

    def execute(self, query: GetProjectQuery) -> ProjectDTO:
        project_id = ProjectId(require_non_empty(query.project_id, field="project_id"))
        self._auth.ensure_can_access_project(query.actor, project_id)
        with self._uow_factory() as uow:
            project = with_domain_errors(lambda: uow.projects.get(project_id))
            return ProjectDTO.from_domain(project)


class ListProjects:
    """List Projects visible to the actor (Project-scoped authorization filter)."""

    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        auth: AuthorizationPort,
    ) -> None:
        self._uow_factory = uow_factory
        self._auth = auth

    def execute(self, query: ListProjectsQuery) -> list[ProjectDTO]:
        with self._uow_factory() as uow:
            projects = with_domain_errors(uow.projects.list_all)
            visible: list[ProjectDTO] = []
            for project in projects:
                try:
                    self._auth.ensure_can_access_project(query.actor, project.id)
                except AuthorizationError:
                    continue
                visible.append(ProjectDTO.from_domain(project))
            return visible
