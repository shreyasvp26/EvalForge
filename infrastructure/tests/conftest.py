"""Shared fixtures for Infrastructure repository tests."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from agent_eval_domain.agent_integration.adapter import Adapter, AdapterVersion
from agent_eval_domain.agent_integration.agent import Agent, AgentVersion
from agent_eval_domain.common.ids import (
    AdapterId,
    AdapterVersionId,
    AgentId,
    AgentVersionId,
    CaseId,
    CaseVersionId,
    GraderId,
    GraderVersionId,
    ProjectId,
    PromptId,
    PromptVersionId,
)
from agent_eval_domain.evaluation_management.case import (
    CaseVersion,
    EvaluationCase,
    Prompt,
    PromptVersion,
    ReferenceRepositoryState,
)
from agent_eval_domain.evaluation_management.project import Project
from agent_eval_domain.grading.grader import Grader, GraderFamily, GraderVersion
from agent_eval_domain.versioning.models import VersionNumber
from agent_eval_domain.versioning.status import VersionStatus
from agent_eval_infrastructure.database.base import Base
from agent_eval_infrastructure.database.engine import create_db_engine, dispose_engine
from agent_eval_infrastructure.database.session import create_session_factory
from agent_eval_infrastructure.repositories import (
    SqlAlchemyAdapterRepository,
    SqlAlchemyAgentRepository,
    SqlAlchemyCaseRepository,
    SqlAlchemyGraderRepository,
    SqlAlchemyProjectRepository,
    SqlAlchemyRunRepository,
    SqlAlchemySuiteRepository,
)
from sqlalchemy.orm import Session, sessionmaker

NOW = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def sqlite_session() -> Session:
    engine = create_db_engine(url="sqlite+pysqlite:///:memory:")
    import agent_eval_infrastructure.database.models  # noqa: F401

    Base.metadata.create_all(engine)
    factory: sessionmaker[Session] = create_session_factory(engine)
    session = factory()
    try:
        yield session
    finally:
        session.close()
        dispose_engine(engine)


@pytest.fixture
def repos(sqlite_session: Session) -> dict[str, object]:
    return {
        "projects": SqlAlchemyProjectRepository(sqlite_session),
        "suites": SqlAlchemySuiteRepository(sqlite_session),
        "cases": SqlAlchemyCaseRepository(sqlite_session),
        "agents": SqlAlchemyAgentRepository(sqlite_session),
        "adapters": SqlAlchemyAdapterRepository(sqlite_session),
        "graders": SqlAlchemyGraderRepository(sqlite_session),
        "runs": SqlAlchemyRunRepository(sqlite_session),
        "session": sqlite_session,
    }


def seed_project(repos: dict[str, object], project_id: str = "proj-1") -> Project:
    project = Project(
        id=ProjectId(project_id),
        name="Demo",
        description="d",
        created_at=NOW,
        settings={"region": "us"},
    )
    repos["projects"].save(project)  # type: ignore[union-attr]
    repos["session"].flush()  # type: ignore[union-attr]
    return project


def seed_agent_adapter(
    repos: dict[str, object],
) -> tuple[Agent, Adapter, AgentVersion, AdapterVersion]:
    agent = Agent(
        id=AgentId("agent-1"),
        name="Codex",
        description="agent",
        created_at=NOW,
    )
    agent_version = AgentVersion(
        id=AgentVersionId("agent-v1"),
        agent_id=agent.id,
        version_number=VersionNumber(1),
        status=VersionStatus.ACTIVE,
        label="v1",
        created_at=NOW,
        predecessor_version_id=None,
    )
    agent._versions = [agent_version]  # noqa: SLF001
    repos["agents"].save(agent)  # type: ignore[union-attr]
    repos["session"].flush()  # type: ignore[union-attr]

    adapter = Adapter(
        id=AdapterId("adapter-1"),
        agent_id=agent.id,
        name="Codex Adapter",
        created_at=NOW,
    )
    adapter_version = AdapterVersion(
        id=AdapterVersionId("adapter-v1"),
        adapter_id=adapter.id,
        version_number=VersionNumber(1),
        status=VersionStatus.ACTIVE,
        label="v1",
        created_at=NOW,
        predecessor_version_id=None,
    )
    adapter._versions = [adapter_version]  # noqa: SLF001
    repos["adapters"].save(adapter)  # type: ignore[union-attr]

    agent.adapter_id = adapter.id
    repos["agents"].save(agent)  # type: ignore[union-attr]
    repos["session"].flush()  # type: ignore[union-attr]
    return agent, adapter, agent_version, adapter_version


def seed_grader(repos: dict[str, object]) -> tuple[Grader, GraderVersion]:
    grader = Grader(
        id=GraderId("grader-1"),
        name="pytest",
        family=GraderFamily.OBJECTIVE,
        description="g",
        created_at=NOW,
    )
    version = GraderVersion(
        id=GraderVersionId("grader-v1"),
        grader_id=grader.id,
        version_number=VersionNumber(1),
        status=VersionStatus.ACTIVE,
        label="v1",
        specification="run pytest",
        created_at=NOW,
        predecessor_version_id=None,
    )
    grader._versions = [version]  # noqa: SLF001
    repos["graders"].save(grader)  # type: ignore[union-attr]
    repos["session"].flush()  # type: ignore[union-attr]
    return grader, version


def seed_case(
    repos: dict[str, object],
    *,
    project_id: ProjectId,
    grader_id: GraderId,
) -> tuple[EvaluationCase, CaseVersion, PromptVersion]:
    prompt = Prompt(id=PromptId("prompt-1"), case_id=CaseId("case-1"), created_at=NOW)
    prompt_version = PromptVersion(
        id=PromptVersionId("prompt-v1"),
        prompt_id=prompt.id,
        version_number=VersionNumber(1),
        status=VersionStatus.ACTIVE,
        content="Fix the bug",
        predecessor_version_id=None,
        created_at=NOW,
    )
    prompt._versions = [prompt_version]  # noqa: SLF001
    case = EvaluationCase(
        id=CaseId("case-1"),
        project_id=project_id,
        name="bugfix",
        prompt=prompt,
        description="a case",
        created_at=NOW,
    )
    case_version = CaseVersion(
        id=CaseVersionId("case-v1"),
        case_id=case.id,
        version_number=VersionNumber(1),
        status=VersionStatus.ACTIVE,
        description="fix auth",
        reference_repository=ReferenceRepositoryState(
            repository_url="https://example.com/repo.git",
            commit_sha="abc1234",
        ),
        expected_checks=("pytest",),
        applicable_grader_ids=(grader_id,),
        prompt_version_id=prompt_version.id,
        predecessor_version_id=None,
        created_at=NOW,
    )
    case._versions = [case_version]  # noqa: SLF001
    repos["cases"].save(case)  # type: ignore[union-attr]
    repos["session"].flush()  # type: ignore[union-attr]
    return case, case_version, prompt_version
