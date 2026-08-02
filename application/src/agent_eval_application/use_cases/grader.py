"""Grader use cases."""

from __future__ import annotations

from agent_eval_domain.common.ids import GraderId, GraderVersionId
from agent_eval_domain.grading.grader import Grader, GraderFamily

from agent_eval_application.commands.grader import (
    CreateGraderCommand,
    CreateGraderDraftVersionCommand,
    PublishGraderVersionCommand,
)
from agent_eval_application.common.id_generator import IdGenerator
from agent_eval_application.common.validation import require_non_empty
from agent_eval_application.dto.grader import GraderDTO, GraderVersionDTO
from agent_eval_application.errors import ApplicationValidationError
from agent_eval_application.ports.authorization import AuthorizationPort
from agent_eval_application.ports.event_dispatcher import DomainEventDispatcher
from agent_eval_application.ports.idempotency import IdempotencyStore
from agent_eval_application.ports.unit_of_work import UnitOfWorkFactory
from agent_eval_application.queries.queries import GetGraderQuery
from agent_eval_application.use_cases.base import (
    collect_events,
    replay_or_begin,
    run_in_uow,
    store_idempotent_result,
    with_domain_errors,
)


class CreateGrader:
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

    def execute(self, command: CreateGraderCommand) -> GraderDTO:
        name = require_non_empty(command.name, field="name")
        family_raw = require_non_empty(command.family, field="family").lower()
        try:
            family = GraderFamily(family_raw)
        except ValueError as exc:
            raise ApplicationValidationError(
                f"Unknown grader family: {command.family}",
                code="INVALID_GRADER_FAMILY",
                details={"family": command.family},
                cause=exc,
            ) from exc

        self._auth.ensure_can_create_project(command.actor)

        replayed = replay_or_begin(
            self._idempotency,
            key=command.idempotency_key,
            scope="create_grader",
            actor=command.actor,
            rebuild=lambda p: _refetch_grader(self._uow_factory, p["id"]),
        )
        if replayed is not None:
            return replayed

        grader_id = GraderId(self._ids.new_id())

        def work(uow):
            grader = with_domain_errors(
                lambda: Grader.create(
                    grader_id=grader_id,
                    name=name,
                    family=family,
                    description=command.description,
                )
            )
            uow.graders.save(grader)
            return GraderDTO.from_domain(grader), collect_events(grader)

        result = run_in_uow(self._uow_factory, self._events, work)
        store_idempotent_result(
            self._idempotency,
            key=command.idempotency_key,
            scope="create_grader",
            actor=command.actor,
            result=result,
        )
        return result


def _refetch_grader(uow_factory: UnitOfWorkFactory, grader_id: str) -> GraderDTO:
    with uow_factory() as uow:
        grader = with_domain_errors(lambda: uow.graders.get(GraderId(grader_id)))
        return GraderDTO.from_domain(grader)


class CreateGraderDraftVersion:
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

    def execute(self, command: CreateGraderDraftVersionCommand) -> GraderVersionDTO:
        grader_id = GraderId(require_non_empty(command.grader_id, field="grader_id"))
        label = require_non_empty(command.label, field="label")
        specification = require_non_empty(command.specification, field="specification")
        self._auth.ensure_can_create_project(command.actor)

        def work(uow):
            grader = uow.graders.get(grader_id)
            version = with_domain_errors(
                lambda: grader.create_draft_version(
                    version_id=GraderVersionId(self._ids.new_id()),
                    label=label,
                    specification=specification,
                )
            )
            uow.graders.save(grader)
            return GraderVersionDTO.from_domain(version), collect_events(grader)

        return run_in_uow(self._uow_factory, self._events, work)


class PublishGraderVersion:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        auth: AuthorizationPort,
        events: DomainEventDispatcher,
    ) -> None:
        self._uow_factory = uow_factory
        self._auth = auth
        self._events = events

    def execute(self, command: PublishGraderVersionCommand) -> GraderVersionDTO:
        grader_id = GraderId(require_non_empty(command.grader_id, field="grader_id"))
        version_id = GraderVersionId(
            require_non_empty(command.version_id, field="version_id")
        )
        self._auth.ensure_can_create_project(command.actor)

        def work(uow):
            grader = uow.graders.get(grader_id)
            version = with_domain_errors(lambda: grader.publish_version(version_id))
            uow.graders.save(grader)
            return GraderVersionDTO.from_domain(version), collect_events(grader)

        return run_in_uow(self._uow_factory, self._events, work)


class GetGrader:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        auth: AuthorizationPort,
    ) -> None:
        self._uow_factory = uow_factory
        self._auth = auth

    def execute(self, query: GetGraderQuery) -> GraderDTO:
        grader_id = GraderId(require_non_empty(query.grader_id, field="grader_id"))
        self._auth.ensure_can_create_project(query.actor)
        with self._uow_factory() as uow:
            grader = with_domain_errors(lambda: uow.graders.get(grader_id))
            return GraderDTO.from_domain(grader)
