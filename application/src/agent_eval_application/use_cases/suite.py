"""Suite use cases."""

from __future__ import annotations

from datetime import datetime

from agent_eval_domain.common.ids import (
    CaseVersionId,
    ProjectId,
    SuiteId,
    SuiteVersionId,
)
from agent_eval_domain.evaluation_management.suite import (
    EvaluationSuite,
    SuiteCompositionEntry,
)

from agent_eval_application.commands.suite import (
    CreateSuiteCommand,
    CreateSuiteDraftVersionCommand,
    DeprecateSuiteCommand,
    PublishSuiteVersionCommand,
    RetireSuiteVersionCommand,
    UpdateSuiteCatalogCommand,
)
from agent_eval_application.common.id_generator import IdGenerator
from agent_eval_application.common.validation import require_non_empty
from agent_eval_application.dto.suite import (
    BenchmarkCatalogEntryDTO,
    SuiteCompositionEntryDTO,
    SuiteDTO,
    SuiteVersionDTO,
)
from agent_eval_application.errors import ApplicationValidationError
from agent_eval_application.ports.authorization import AuthorizationPort
from agent_eval_application.ports.event_dispatcher import DomainEventDispatcher
from agent_eval_application.ports.idempotency import IdempotencyStore
from agent_eval_application.ports.unit_of_work import UnitOfWorkFactory
from agent_eval_application.queries.queries import (
    GetSuiteQuery,
    ListSuitesByProjectQuery,
)
from agent_eval_application.use_cases.base import (
    collect_events,
    replay_or_begin,
    run_in_uow,
    store_idempotent_result,
    with_domain_errors,
)


def _parse_dt(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


def _rebuild_suite_version(payload: dict) -> SuiteVersionDTO:
    return SuiteVersionDTO(
        id=payload["id"],
        suite_id=payload["suite_id"],
        version_number=payload["version_number"],
        status=payload["status"],
        composition=tuple(
            SuiteCompositionEntryDTO(**entry) for entry in payload["composition"]
        ),
        predecessor_version_id=payload["predecessor_version_id"],
        created_at=_parse_dt(payload["created_at"]),
    )


def _rebuild_suite(payload: dict) -> SuiteDTO:
    return SuiteDTO(
        id=payload["id"],
        project_id=payload["project_id"],
        name=payload["name"],
        description=payload["description"],
        catalog_key=payload.get("catalog_key", ""),
        catalog_visible=bool(payload.get("catalog_visible", False)),
        status=payload["status"],
        created_at=_parse_dt(payload["created_at"]),
        active_version_id=payload["active_version_id"],
        versions=tuple(_rebuild_suite_version(v) for v in payload["versions"]),
    )


class CreateSuite:
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

    def execute(self, command: CreateSuiteCommand) -> SuiteDTO:
        name = require_non_empty(command.name, field="name")
        project_id = ProjectId(
            require_non_empty(command.project_id, field="project_id")
        )
        self._auth.ensure_can_manage_project(command.actor, project_id)

        replayed = replay_or_begin(
            self._idempotency,
            key=command.idempotency_key,
            scope=f"create_suite:{project_id.value}",
            actor=command.actor,
            rebuild=_rebuild_suite,
        )
        if replayed is not None:
            return replayed

        suite_id = SuiteId(self._ids.new_id())

        def work(uow):
            project = uow.projects.get(project_id)
            if not project.is_active():
                raise ApplicationValidationError(
                    "Cannot create Suite on a deprecated Project",
                    code="PROJECT_NOT_ACTIVE",
                    details={"project_id": project_id.value},
                )
            suite = with_domain_errors(
                lambda: EvaluationSuite.create(
                    suite_id=suite_id,
                    project_id=project_id,
                    name=name,
                    description=command.description,
                    catalog_key=command.catalog_key,
                    catalog_visible=command.catalog_visible,
                )
            )
            uow.suites.save(suite)
            return SuiteDTO.from_domain(suite), collect_events(suite)

        result = run_in_uow(self._uow_factory, self._events, work)
        store_idempotent_result(
            self._idempotency,
            key=command.idempotency_key,
            scope=f"create_suite:{project_id.value}",
            actor=command.actor,
            result=result,
        )
        return result


class CreateSuiteDraftVersion:
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

    def execute(self, command: CreateSuiteDraftVersionCommand) -> SuiteVersionDTO:
        suite_id = SuiteId(require_non_empty(command.suite_id, field="suite_id"))

        def work(uow):
            suite = uow.suites.get(suite_id)
            self._auth.ensure_can_manage_project(command.actor, suite.project_id)
            composition = [
                SuiteCompositionEntry(
                    case_version_id=CaseVersionId(
                        require_non_empty(
                            entry.case_version_id, field="case_version_id"
                        )
                    ),
                    position=entry.position,
                    case_project_id=ProjectId(
                        require_non_empty(
                            entry.case_project_id, field="case_project_id"
                        )
                    ),
                )
                for entry in command.composition
            ]
            version = with_domain_errors(
                lambda: suite.create_draft_version(
                    version_id=SuiteVersionId(self._ids.new_id()),
                    composition=composition,
                )
            )
            uow.suites.save(suite)
            return SuiteVersionDTO.from_domain(version), collect_events(suite)

        return run_in_uow(self._uow_factory, self._events, work)


class PublishSuiteVersion:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        auth: AuthorizationPort,
        events: DomainEventDispatcher,
    ) -> None:
        self._uow_factory = uow_factory
        self._auth = auth
        self._events = events

    def execute(self, command: PublishSuiteVersionCommand) -> SuiteVersionDTO:
        suite_id = SuiteId(require_non_empty(command.suite_id, field="suite_id"))
        version_id = SuiteVersionId(
            require_non_empty(command.version_id, field="version_id")
        )

        def work(uow):
            suite = uow.suites.get(suite_id)
            self._auth.ensure_can_manage_project(command.actor, suite.project_id)
            version = with_domain_errors(lambda: suite.publish_version(version_id))
            uow.suites.save(suite)
            return SuiteVersionDTO.from_domain(version), collect_events(suite)

        return run_in_uow(self._uow_factory, self._events, work)


class RetireSuiteVersion:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        auth: AuthorizationPort,
        events: DomainEventDispatcher,
    ) -> None:
        self._uow_factory = uow_factory
        self._auth = auth
        self._events = events

    def execute(self, command: RetireSuiteVersionCommand) -> SuiteVersionDTO:
        suite_id = SuiteId(require_non_empty(command.suite_id, field="suite_id"))
        version_id = SuiteVersionId(
            require_non_empty(command.version_id, field="version_id")
        )

        def work(uow):
            suite = uow.suites.get(suite_id)
            self._auth.ensure_can_manage_project(command.actor, suite.project_id)
            version = with_domain_errors(lambda: suite.retire_version(version_id))
            uow.suites.save(suite)
            return SuiteVersionDTO.from_domain(version), collect_events(suite)

        return run_in_uow(self._uow_factory, self._events, work)


class DeprecateSuite:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        auth: AuthorizationPort,
        events: DomainEventDispatcher,
    ) -> None:
        self._uow_factory = uow_factory
        self._auth = auth
        self._events = events

    def execute(self, command: DeprecateSuiteCommand) -> SuiteDTO:
        suite_id = SuiteId(require_non_empty(command.suite_id, field="suite_id"))

        def work(uow):
            suite = uow.suites.get(suite_id)
            self._auth.ensure_can_manage_project(command.actor, suite.project_id)
            with_domain_errors(suite.deprecate)
            uow.suites.save(suite)
            return SuiteDTO.from_domain(suite), collect_events(suite)

        return run_in_uow(self._uow_factory, self._events, work)


class GetSuite:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        auth: AuthorizationPort,
    ) -> None:
        self._uow_factory = uow_factory
        self._auth = auth

    def execute(self, query: GetSuiteQuery) -> SuiteDTO:
        suite_id = SuiteId(require_non_empty(query.suite_id, field="suite_id"))
        with self._uow_factory() as uow:
            suite = with_domain_errors(lambda: uow.suites.get(suite_id))
            self._auth.ensure_can_access_project(query.actor, suite.project_id)
            return SuiteDTO.from_domain(suite)


class ListSuitesByProject:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        auth: AuthorizationPort,
    ) -> None:
        self._uow_factory = uow_factory
        self._auth = auth

    def execute(self, query: ListSuitesByProjectQuery) -> list[SuiteDTO]:
        project_id = ProjectId(require_non_empty(query.project_id, field="project_id"))
        self._auth.ensure_can_access_project(query.actor, project_id)
        with self._uow_factory() as uow:
            suites = with_domain_errors(lambda: uow.suites.list_by_project(project_id))
            return [SuiteDTO.from_domain(s) for s in suites]


class UpdateSuiteCatalog:
    """Toggle catalog visibility / key on a Suite identity."""

    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        auth: AuthorizationPort,
        events: DomainEventDispatcher,
    ) -> None:
        self._uow_factory = uow_factory
        self._auth = auth
        self._events = events

    def execute(self, command: UpdateSuiteCatalogCommand) -> SuiteDTO:
        suite_id = SuiteId(require_non_empty(command.suite_id, field="suite_id"))

        def work(uow):
            suite = uow.suites.get(suite_id)
            self._auth.ensure_can_manage_project(command.actor, suite.project_id)
            with_domain_errors(
                lambda: suite.set_catalog(
                    catalog_key=command.catalog_key,
                    catalog_visible=command.catalog_visible,
                )
            )
            uow.suites.save(suite)
            return SuiteDTO.from_domain(suite), collect_events(suite)

        return run_in_uow(self._uow_factory, self._events, work)


class ListBenchmarkCatalog:
    """List catalog-visible suites with composition summary for discovery."""

    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        auth: AuthorizationPort,
    ) -> None:
        self._uow_factory = uow_factory
        self._auth = auth

    def execute(
        self, query: ListSuitesByProjectQuery
    ) -> list[BenchmarkCatalogEntryDTO]:
        project_id = ProjectId(require_non_empty(query.project_id, field="project_id"))
        self._auth.ensure_can_access_project(query.actor, project_id)
        with self._uow_factory() as uow:
            suites = with_domain_errors(lambda: uow.suites.list_by_project(project_id))
            entries: list[BenchmarkCatalogEntryDTO] = []
            for suite in suites:
                if not suite.catalog_visible:
                    continue
                active = suite.active_version()
                categories: set[str] = set()
                difficulties: set[str] = set()
                case_count = 0
                if active is not None:
                    case_count = len(active.composition)
                    for entry in active.composition:
                        case_version = with_domain_errors(
                            lambda eid=entry.case_version_id: uow.cases.get_version(eid)
                        )
                        case = with_domain_errors(
                            lambda cid=case_version.case_id: uow.cases.get(cid)
                        )
                        if case.category:
                            categories.add(case.category)
                        if case.difficulty:
                            difficulties.add(case.difficulty)
                entries.append(
                    BenchmarkCatalogEntryDTO(
                        suite_id=suite.id.value,
                        project_id=suite.project_id.value,
                        catalog_key=suite.catalog_key or suite.name,
                        name=suite.name,
                        description=suite.description,
                        status=suite.status.value,
                        active_version_id=active.id.value if active else None,
                        active_version_number=(
                            active.version_number.value if active else None
                        ),
                        case_count=case_count,
                        categories=tuple(sorted(categories)),
                        difficulties=tuple(sorted(difficulties)),
                        created_at=suite.created_at,
                        catalog_visible=suite.catalog_visible,
                    )
                )
            entries.sort(key=lambda e: (e.catalog_key, e.name))
            return entries
