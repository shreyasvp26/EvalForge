"""Domain-defined repository contracts. Infrastructure implements these later."""

from __future__ import annotations

from typing import Protocol

from agent_eval_domain.agent_integration.adapter import Adapter
from agent_eval_domain.agent_integration.agent import Agent
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


class ProjectRepository(Protocol):
    def get(self, project_id: ProjectId) -> Project: ...

    def save(self, project: Project) -> None: ...

    def list_all(self) -> list[Project]: ...


class SuiteRepository(Protocol):
    def get(self, suite_id: SuiteId) -> EvaluationSuite: ...

    def get_version(self, suite_version_id: SuiteVersionId) -> SuiteVersion: ...

    def save(self, suite: EvaluationSuite) -> None: ...

    def list_by_project(self, project_id: ProjectId) -> list[EvaluationSuite]: ...


class CaseRepository(Protocol):
    def get(self, case_id: CaseId) -> EvaluationCase: ...

    def get_version(self, case_version_id: CaseVersionId) -> CaseVersion: ...

    def save(self, case: EvaluationCase) -> None: ...

    def list_by_project(self, project_id: ProjectId) -> list[EvaluationCase]: ...


class AgentRepository(Protocol):
    def get(self, agent_id: AgentId) -> Agent: ...

    def save(self, agent: Agent) -> None: ...

    def list_all(self) -> list[Agent]: ...


class AdapterRepository(Protocol):
    def get(self, adapter_id: AdapterId) -> Adapter: ...

    def get_by_agent(self, agent_id: AgentId) -> Adapter: ...

    def save(self, adapter: Adapter) -> None: ...

    def list_all(self) -> list[Adapter]: ...


class GraderRepository(Protocol):
    def get(self, grader_id: GraderId) -> Grader: ...

    def save(self, grader: Grader) -> None: ...

    def list_all(self) -> list[Grader]: ...


class RunRepository(Protocol):
    def get(self, run_id: RunId) -> EvaluationRun: ...

    def save(self, run: EvaluationRun) -> None: ...

    def list_by_project(self, project_id: ProjectId) -> list[EvaluationRun]: ...
