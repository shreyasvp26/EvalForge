"""Agent and Adapter use cases."""

from __future__ import annotations

from agent_eval_domain.agent_integration.adapter import Adapter
from agent_eval_domain.agent_integration.agent import Agent
from agent_eval_domain.common.ids import (
    AdapterId,
    AdapterVersionId,
    AgentId,
    AgentVersionId,
)

from agent_eval_application.commands.agent import (
    CreateAdapterCommand,
    CreateAdapterDraftVersionCommand,
    CreateAgentCommand,
    CreateAgentDraftVersionCommand,
    PublishAdapterVersionCommand,
    PublishAgentVersionCommand,
)
from agent_eval_application.common.id_generator import IdGenerator
from agent_eval_application.common.validation import require_non_empty
from agent_eval_application.dto.agent import (
    AdapterDTO,
    AdapterVersionDTO,
    AgentDTO,
    AgentVersionDTO,
)
from agent_eval_application.ports.authorization import AuthorizationPort
from agent_eval_application.ports.event_dispatcher import DomainEventDispatcher
from agent_eval_application.ports.idempotency import IdempotencyStore
from agent_eval_application.ports.unit_of_work import UnitOfWorkFactory
from agent_eval_application.queries.queries import GetAgentQuery
from agent_eval_application.use_cases.base import (
    collect_events,
    replay_or_begin,
    run_in_uow,
    store_idempotent_result,
    with_domain_errors,
)


class CreateAgent:
    """Create an Agent identity. Platform-scoped (not Project-scoped)."""

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

    def execute(self, command: CreateAgentCommand) -> AgentDTO:
        name = require_non_empty(command.name, field="name")
        # Platform-level create uses the same create-project gate for now
        # (authorization policy is Infrastructure-pluggable).
        self._auth.ensure_can_create_project(command.actor)

        replayed = replay_or_begin(
            self._idempotency,
            key=command.idempotency_key,
            scope="create_agent",
            actor=command.actor,
            rebuild=lambda p: _refetch_agent(self._uow_factory, p["id"]),
        )
        if replayed is not None:
            return replayed

        agent_id = AgentId(self._ids.new_id())

        def work(uow):
            agent = with_domain_errors(
                lambda: Agent.create(
                    agent_id=agent_id,
                    name=name,
                    description=command.description,
                )
            )
            uow.agents.save(agent)
            return AgentDTO.from_domain(agent), collect_events(agent)

        result = run_in_uow(self._uow_factory, self._events, work)
        store_idempotent_result(
            self._idempotency,
            key=command.idempotency_key,
            scope="create_agent",
            actor=command.actor,
            result=result,
        )
        return result


def _refetch_agent(uow_factory: UnitOfWorkFactory, agent_id: str) -> AgentDTO:
    with uow_factory() as uow:
        agent = with_domain_errors(lambda: uow.agents.get(AgentId(agent_id)))
        return AgentDTO.from_domain(agent)


class CreateAgentDraftVersion:
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

    def execute(self, command: CreateAgentDraftVersionCommand) -> AgentVersionDTO:
        agent_id = AgentId(require_non_empty(command.agent_id, field="agent_id"))
        label = require_non_empty(command.label, field="label")
        self._auth.ensure_can_create_project(command.actor)

        def work(uow):
            agent = uow.agents.get(agent_id)
            version = with_domain_errors(
                lambda: agent.create_draft_version(
                    version_id=AgentVersionId(self._ids.new_id()),
                    label=label,
                    release_notes=command.release_notes,
                )
            )
            uow.agents.save(agent)
            return AgentVersionDTO.from_domain(version), collect_events(agent)

        return run_in_uow(self._uow_factory, self._events, work)


class PublishAgentVersion:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        auth: AuthorizationPort,
        events: DomainEventDispatcher,
    ) -> None:
        self._uow_factory = uow_factory
        self._auth = auth
        self._events = events

    def execute(self, command: PublishAgentVersionCommand) -> AgentVersionDTO:
        agent_id = AgentId(require_non_empty(command.agent_id, field="agent_id"))
        version_id = AgentVersionId(
            require_non_empty(command.version_id, field="version_id")
        )
        self._auth.ensure_can_create_project(command.actor)

        def work(uow):
            agent = uow.agents.get(agent_id)
            version = with_domain_errors(lambda: agent.publish_version(version_id))
            uow.agents.save(agent)
            return AgentVersionDTO.from_domain(version), collect_events(agent)

        return run_in_uow(self._uow_factory, self._events, work)


class CreateAdapter:
    """Create Adapter and connect it to its Agent in one unit of work."""

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

    def execute(self, command: CreateAdapterCommand) -> AdapterDTO:
        name = require_non_empty(command.name, field="name")
        agent_id = AgentId(require_non_empty(command.agent_id, field="agent_id"))
        self._auth.ensure_can_create_project(command.actor)

        replayed = replay_or_begin(
            self._idempotency,
            key=command.idempotency_key,
            scope=f"create_adapter:{agent_id.value}",
            actor=command.actor,
            rebuild=lambda p: _refetch_adapter(self._uow_factory, p["id"]),
        )
        if replayed is not None:
            return replayed

        adapter_id = AdapterId(self._ids.new_id())

        def work(uow):
            agent = uow.agents.get(agent_id)
            adapter = with_domain_errors(
                lambda: Adapter.create(
                    adapter_id=adapter_id,
                    agent_id=agent_id,
                    name=name,
                )
            )
            with_domain_errors(lambda: agent.connect_adapter(adapter_id))
            uow.adapters.save(adapter)
            uow.agents.save(agent)
            return AdapterDTO.from_domain(adapter), collect_events(adapter, agent)

        result = run_in_uow(self._uow_factory, self._events, work)
        store_idempotent_result(
            self._idempotency,
            key=command.idempotency_key,
            scope=f"create_adapter:{agent_id.value}",
            actor=command.actor,
            result=result,
        )
        return result


def _refetch_adapter(uow_factory: UnitOfWorkFactory, adapter_id: str) -> AdapterDTO:
    with uow_factory() as uow:
        adapter = with_domain_errors(lambda: uow.adapters.get(AdapterId(adapter_id)))
        return AdapterDTO.from_domain(adapter)


class CreateAdapterDraftVersion:
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

    def execute(self, command: CreateAdapterDraftVersionCommand) -> AdapterVersionDTO:
        adapter_id = AdapterId(
            require_non_empty(command.adapter_id, field="adapter_id")
        )
        label = require_non_empty(command.label, field="label")
        self._auth.ensure_can_create_project(command.actor)

        def work(uow):
            adapter = uow.adapters.get(adapter_id)
            version = with_domain_errors(
                lambda: adapter.create_draft_version(
                    version_id=AdapterVersionId(self._ids.new_id()),
                    label=label,
                    notes=command.notes,
                )
            )
            uow.adapters.save(adapter)
            return AdapterVersionDTO.from_domain(version), collect_events(adapter)

        return run_in_uow(self._uow_factory, self._events, work)


class PublishAdapterVersion:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        auth: AuthorizationPort,
        events: DomainEventDispatcher,
    ) -> None:
        self._uow_factory = uow_factory
        self._auth = auth
        self._events = events

    def execute(self, command: PublishAdapterVersionCommand) -> AdapterVersionDTO:
        adapter_id = AdapterId(
            require_non_empty(command.adapter_id, field="adapter_id")
        )
        version_id = AdapterVersionId(
            require_non_empty(command.version_id, field="version_id")
        )
        self._auth.ensure_can_create_project(command.actor)

        def work(uow):
            adapter = uow.adapters.get(adapter_id)
            version = with_domain_errors(lambda: adapter.publish_version(version_id))
            uow.adapters.save(adapter)
            return AdapterVersionDTO.from_domain(version), collect_events(adapter)

        return run_in_uow(self._uow_factory, self._events, work)


class GetAgent:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        auth: AuthorizationPort,
    ) -> None:
        self._uow_factory = uow_factory
        self._auth = auth

    def execute(self, query: GetAgentQuery) -> AgentDTO:
        agent_id = AgentId(require_non_empty(query.agent_id, field="agent_id"))
        # Read access for agents: any authenticated actor that can create projects
        # may read agent catalog; finer policies plug in via AuthorizationPort.
        self._auth.ensure_can_create_project(query.actor)
        with self._uow_factory() as uow:
            agent = with_domain_errors(lambda: uow.agents.get(agent_id))
            return AgentDTO.from_domain(agent)
