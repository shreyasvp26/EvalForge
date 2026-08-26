"""Platform catalog use cases."""

from __future__ import annotations

from agent_eval_domain.common.ids import PlatformId, PlatformVersionId
from agent_eval_domain.platform.platform import Platform

from agent_eval_application.commands.platform import (
    CreatePlatformCommand,
    CreatePlatformDraftVersionCommand,
    PublishPlatformVersionCommand,
)
from agent_eval_application.common.id_generator import IdGenerator
from agent_eval_application.common.validation import require_non_empty
from agent_eval_application.dto.platform import PlatformDTO, PlatformVersionDTO
from agent_eval_application.ports.authorization import AuthorizationPort
from agent_eval_application.ports.event_dispatcher import DomainEventDispatcher
from agent_eval_application.ports.idempotency import IdempotencyStore
from agent_eval_application.ports.unit_of_work import UnitOfWorkFactory
from agent_eval_application.queries.queries import GetPlatformQuery, ListPlatformsQuery
from agent_eval_application.use_cases.base import (
    collect_events,
    replay_or_begin,
    run_in_uow,
    store_idempotent_result,
    with_domain_errors,
)


def _refetch_platform(uow_factory: UnitOfWorkFactory, platform_id: str) -> PlatformDTO:
    with uow_factory() as uow:
        platform = with_domain_errors(
            lambda: uow.platforms.get(PlatformId(platform_id))
        )
        return PlatformDTO.from_domain(platform)


class CreatePlatform:
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

    def execute(self, command: CreatePlatformCommand) -> PlatformDTO:
        name = require_non_empty(command.name, field="name")
        self._auth.ensure_can_create_project(command.actor)
        replayed = replay_or_begin(
            self._idempotency,
            key=command.idempotency_key,
            scope="create_platform",
            actor=command.actor,
            rebuild=lambda payload: _refetch_platform(self._uow_factory, payload["id"]),
        )
        if replayed is not None:
            return replayed
        platform_id = PlatformId(self._ids.new_id())

        def work(uow):
            platform = with_domain_errors(
                lambda: Platform.create(platform_id=platform_id, name=name)
            )
            uow.platforms.save(platform)
            return PlatformDTO.from_domain(platform), collect_events(platform)

        result = run_in_uow(self._uow_factory, self._events, work)
        store_idempotent_result(
            self._idempotency,
            key=command.idempotency_key,
            scope="create_platform",
            actor=command.actor,
            result=result,
        )
        return result


class CreatePlatformDraftVersion:
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

    def execute(self, command: CreatePlatformDraftVersionCommand) -> PlatformVersionDTO:
        platform_id = PlatformId(
            require_non_empty(command.platform_id, field="platform_id")
        )
        label = require_non_empty(command.label, field="label")
        self._auth.ensure_can_create_project(command.actor)

        def work(uow):
            platform = uow.platforms.get(platform_id)
            version = with_domain_errors(
                lambda: platform.create_draft_version(
                    version_id=PlatformVersionId(self._ids.new_id()),
                    label=label,
                    sandbox_policy=command.sandbox_policy,
                    execution_policy=command.execution_policy,
                    timeout_policy=command.timeout_policy,
                    environment_policy=command.environment_policy,
                    grading_policy=command.grading_policy,
                    notes=command.notes,
                )
            )
            uow.platforms.save(platform)
            return PlatformVersionDTO.from_domain(version), collect_events(platform)

        return run_in_uow(self._uow_factory, self._events, work)


class PublishPlatformVersion:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        auth: AuthorizationPort,
        events: DomainEventDispatcher,
    ) -> None:
        self._uow_factory = uow_factory
        self._auth = auth
        self._events = events

    def execute(self, command: PublishPlatformVersionCommand) -> PlatformVersionDTO:
        platform_id = PlatformId(
            require_non_empty(command.platform_id, field="platform_id")
        )
        version_id = PlatformVersionId(
            require_non_empty(command.version_id, field="version_id")
        )
        self._auth.ensure_can_create_project(command.actor)

        def work(uow):
            platform = uow.platforms.get(platform_id)
            version = with_domain_errors(lambda: platform.publish_version(version_id))
            uow.platforms.save(platform)
            return PlatformVersionDTO.from_domain(version), collect_events(platform)

        return run_in_uow(self._uow_factory, self._events, work)


class GetPlatform:
    def __init__(self, uow_factory: UnitOfWorkFactory, auth: AuthorizationPort) -> None:
        self._uow_factory = uow_factory
        self._auth = auth

    def execute(self, query: GetPlatformQuery) -> PlatformDTO:
        platform_id = PlatformId(
            require_non_empty(query.platform_id, field="platform_id")
        )
        self._auth.ensure_can_create_project(query.actor)
        with self._uow_factory() as uow:
            return PlatformDTO.from_domain(
                with_domain_errors(lambda: uow.platforms.get(platform_id))
            )


class ListPlatforms:
    def __init__(self, uow_factory: UnitOfWorkFactory, auth: AuthorizationPort) -> None:
        self._uow_factory = uow_factory
        self._auth = auth

    def execute(self, query: ListPlatformsQuery) -> list[PlatformDTO]:
        self._auth.ensure_can_create_project(query.actor)
        with self._uow_factory() as uow:
            platforms = with_domain_errors(uow.platforms.list_all)
            return [PlatformDTO.from_domain(platform) for platform in platforms]
