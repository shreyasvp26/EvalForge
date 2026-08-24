"""In-memory fakes for Application unit tests — never a real database."""

from __future__ import annotations

import copy
from types import TracebackType
from typing import Any

from agent_eval_application.common.actor import Actor
from agent_eval_application.errors import AuthorizationError
from agent_eval_application.ports.idempotency import (
    IdempotencyRecord,
    IdempotencyStatus,
)
from agent_eval_domain.agent_integration.adapter import Adapter
from agent_eval_domain.agent_integration.agent import Agent
from agent_eval_domain.common.errors import NotFoundError
from agent_eval_domain.common.events import DomainEvent
from agent_eval_domain.common.ids import (
    AdapterId,
    AgentId,
    CaseId,
    CaseVersionId,
    GraderId,
    ProjectId,
    RunId,
    SuiteId,
    SuiteVersionId,
)
from agent_eval_domain.evaluation_management.case import CaseVersion, EvaluationCase
from agent_eval_domain.evaluation_management.project import Project
from agent_eval_domain.evaluation_management.suite import EvaluationSuite, SuiteVersion
from agent_eval_domain.execution.run import EvaluationRun
from agent_eval_domain.grading.grader import Grader


class InMemoryIdGenerator:
    def __init__(self, prefix: str = "id") -> None:
        self._n = 0
        self._prefix = prefix

    def new_id(self) -> str:
        self._n += 1
        return f"{self._prefix}-{self._n}"


class AllowAllAuth:
    def __init__(self) -> None:
        self.granted_owners: list[tuple[str, str]] = []

    def ensure_can_access_project(self, actor: Actor, project_id: ProjectId) -> None:
        return None

    def ensure_can_manage_project(self, actor: Actor, project_id: ProjectId) -> None:
        return None

    def ensure_can_create_project(self, actor: Actor) -> None:
        return None

    def grant_project_owner(self, actor: Actor, project_id: ProjectId) -> None:
        self.granted_owners.append((actor.id, project_id.value))


class DenyAllAuth:
    def ensure_can_access_project(self, actor: Actor, project_id: ProjectId) -> None:
        raise AuthorizationError(details={"project_id": project_id.value})

    def ensure_can_manage_project(self, actor: Actor, project_id: ProjectId) -> None:
        raise AuthorizationError(details={"project_id": project_id.value})

    def ensure_can_create_project(self, actor: Actor) -> None:
        raise AuthorizationError()

    def grant_project_owner(self, actor: Actor, project_id: ProjectId) -> None:
        raise AuthorizationError(details={"project_id": project_id.value})


class RecordingEventDispatcher:
    def __init__(self) -> None:
        self.events: list[DomainEvent] = []

    def dispatch(self, events) -> None:
        self.events.extend(events)


class RecordingRunQueue:
    def __init__(self) -> None:
        self.enqueued: list[RunId] = []

    def enqueue_run(self, run_id: RunId) -> None:
        self.enqueued.append(run_id)


class InMemoryIdempotencyStore:
    def __init__(self) -> None:
        self._records: dict[tuple[str, str], IdempotencyRecord] = {}

    def get(self, *, key: str, scope: str) -> IdempotencyRecord | None:
        return self._records.get((key, scope))

    def put_completed(
        self,
        *,
        key: str,
        scope: str,
        result: dict[str, Any],
    ) -> None:
        self._records[(key, scope)] = IdempotencyRecord(
            key=key,
            scope=scope,
            status=IdempotencyStatus.COMPLETED,
            result=result,
        )


class InMemoryUnitOfWork:
    def __init__(self, store: SharedStore) -> None:
        self._store = store
        self.projects = store.projects
        self.suites = store.suites
        self.cases = store.cases
        self.agents = store.agents
        self.adapters = store.adapters
        self.graders = store.graders
        self.runs = store.runs
        self.committed = False
        self.rolled_back = False

    def commit(self) -> None:
        self.committed = True
        self._store.snapshot()

    def rollback(self) -> None:
        self.rolled_back = True
        self._store.restore()

    def __enter__(self) -> InMemoryUnitOfWork:
        self._store.begin()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if exc is not None and not self.committed:
            self.rollback()


class InMemoryUnitOfWorkFactory:
    def __init__(self, store: SharedStore) -> None:
        self.store = store

    def __call__(self) -> InMemoryUnitOfWork:
        return InMemoryUnitOfWork(self.store)


class _ProjectRepo:
    def __init__(self, data: dict[str, Project]) -> None:
        self._data = data

    def get(self, project_id: ProjectId) -> Project:
        try:
            return self._data[project_id.value]
        except KeyError as exc:
            raise NotFoundError(
                "Project not found",
                entity="Project",
                entity_id=project_id.value,
            ) from exc

    def save(self, project: Project) -> None:
        self._data[project.id.value] = project

    def list_all(self) -> list[Project]:
        return list(self._data.values())


class _SuiteRepo:
    def __init__(
        self, data: dict[str, EvaluationSuite], versions: dict[str, SuiteVersion]
    ) -> None:
        self._data = data
        self._versions = versions

    def get(self, suite_id: SuiteId) -> EvaluationSuite:
        try:
            return self._data[suite_id.value]
        except KeyError as exc:
            raise NotFoundError(
                "Suite not found",
                entity="EvaluationSuite",
                entity_id=suite_id.value,
            ) from exc

    def get_version(self, suite_version_id: SuiteVersionId) -> SuiteVersion:
        try:
            return self._versions[suite_version_id.value]
        except KeyError as exc:
            raise NotFoundError(
                "Suite version not found",
                entity="SuiteVersion",
                entity_id=suite_version_id.value,
            ) from exc

    def save(self, suite: EvaluationSuite) -> None:
        self._data[suite.id.value] = suite
        for version in suite.versions:
            self._versions[version.id.value] = version

    def list_by_project(self, project_id: ProjectId) -> list[EvaluationSuite]:
        return [s for s in self._data.values() if s.project_id == project_id]


class _CaseRepo:
    def __init__(
        self, data: dict[str, EvaluationCase], versions: dict[str, CaseVersion]
    ) -> None:
        self._data = data
        self._versions = versions

    def get(self, case_id: CaseId) -> EvaluationCase:
        try:
            return self._data[case_id.value]
        except KeyError as exc:
            raise NotFoundError(
                "Case not found",
                entity="EvaluationCase",
                entity_id=case_id.value,
            ) from exc

    def get_version(self, case_version_id: CaseVersionId) -> CaseVersion:
        try:
            return self._versions[case_version_id.value]
        except KeyError as exc:
            raise NotFoundError(
                "Case version not found",
                entity="CaseVersion",
                entity_id=case_version_id.value,
            ) from exc

    def save(self, case: EvaluationCase) -> None:
        self._data[case.id.value] = case
        for version in case.versions:
            self._versions[version.id.value] = version

    def list_by_project(self, project_id: ProjectId) -> list[EvaluationCase]:
        return [c for c in self._data.values() if c.project_id == project_id]


class _AgentRepo:
    def __init__(self, data: dict[str, Agent]) -> None:
        self._data = data

    def get(self, agent_id: AgentId) -> Agent:
        try:
            return self._data[agent_id.value]
        except KeyError as exc:
            raise NotFoundError(
                "Agent not found",
                entity="Agent",
                entity_id=agent_id.value,
            ) from exc

    def save(self, agent: Agent) -> None:
        self._data[agent.id.value] = agent

    def list_all(self) -> list[Agent]:
        return list(self._data.values())


class _AdapterRepo:
    def __init__(self, data: dict[str, Adapter]) -> None:
        self._data = data

    def get(self, adapter_id: AdapterId) -> Adapter:
        try:
            return self._data[adapter_id.value]
        except KeyError as exc:
            raise NotFoundError(
                "Adapter not found",
                entity="Adapter",
                entity_id=adapter_id.value,
            ) from exc

    def get_by_agent(self, agent_id: AgentId) -> Adapter:
        for adapter in self._data.values():
            if adapter.agent_id == agent_id:
                return adapter
        raise NotFoundError(
            "Adapter not found for agent",
            entity="Adapter",
            entity_id=agent_id.value,
        )

    def save(self, adapter: Adapter) -> None:
        self._data[adapter.id.value] = adapter

    def list_all(self) -> list[Adapter]:
        return list(self._data.values())


class _GraderRepo:
    def __init__(self, data: dict[str, Grader]) -> None:
        self._data = data

    def get(self, grader_id: GraderId) -> Grader:
        try:
            return self._data[grader_id.value]
        except KeyError as exc:
            raise NotFoundError(
                "Grader not found",
                entity="Grader",
                entity_id=grader_id.value,
            ) from exc

    def save(self, grader: Grader) -> None:
        self._data[grader.id.value] = grader

    def list_all(self) -> list[Grader]:
        return list(self._data.values())


class _RunRepo:
    def __init__(self, data: dict[str, EvaluationRun]) -> None:
        self._data = data

    def get(self, run_id: RunId) -> EvaluationRun:
        try:
            return self._data[run_id.value]
        except KeyError as exc:
            raise NotFoundError(
                "Run not found",
                entity="EvaluationRun",
                entity_id=run_id.value,
            ) from exc

    def save(self, run: EvaluationRun) -> None:
        self._data[run.id.value] = run

    def list_by_project(self, project_id: ProjectId) -> list[EvaluationRun]:
        return [r for r in self._data.values() if r.pins.project_id == project_id]


class SharedStore:
    """Mutable in-memory persistence shared across UoW instances in a test."""

    def __init__(self) -> None:
        self._projects: dict[str, Project] = {}
        self._suites: dict[str, EvaluationSuite] = {}
        self._suite_versions: dict[str, SuiteVersion] = {}
        self._cases: dict[str, EvaluationCase] = {}
        self._case_versions: dict[str, CaseVersion] = {}
        self._agents: dict[str, Agent] = {}
        self._adapters: dict[str, Adapter] = {}
        self._graders: dict[str, Grader] = {}
        self._runs: dict[str, EvaluationRun] = {}
        self._backup: dict[str, Any] | None = None

        self.projects = _ProjectRepo(self._projects)
        self.suites = _SuiteRepo(self._suites, self._suite_versions)
        self.cases = _CaseRepo(self._cases, self._case_versions)
        self.agents = _AgentRepo(self._agents)
        self.adapters = _AdapterRepo(self._adapters)
        self.graders = _GraderRepo(self._graders)
        self.runs = _RunRepo(self._runs)

    def begin(self) -> None:
        self._backup = {
            "projects": copy.deepcopy(self._projects),
            "suites": copy.deepcopy(self._suites),
            "suite_versions": copy.deepcopy(self._suite_versions),
            "cases": copy.deepcopy(self._cases),
            "case_versions": copy.deepcopy(self._case_versions),
            "agents": copy.deepcopy(self._agents),
            "adapters": copy.deepcopy(self._adapters),
            "graders": copy.deepcopy(self._graders),
            "runs": copy.deepcopy(self._runs),
        }

    def snapshot(self) -> None:
        self._backup = None

    def restore(self) -> None:
        if self._backup is None:
            return
        self._projects.clear()
        self._projects.update(self._backup["projects"])
        self._suites.clear()
        self._suites.update(self._backup["suites"])
        self._suite_versions.clear()
        self._suite_versions.update(self._backup["suite_versions"])
        self._cases.clear()
        self._cases.update(self._backup["cases"])
        self._case_versions.clear()
        self._case_versions.update(self._backup["case_versions"])
        self._agents.clear()
        self._agents.update(self._backup["agents"])
        self._adapters.clear()
        self._adapters.update(self._backup["adapters"])
        self._graders.clear()
        self._graders.update(self._backup["graders"])
        self._runs.clear()
        self._runs.update(self._backup["runs"])
        self._backup = None
