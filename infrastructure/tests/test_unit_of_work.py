"""Unit of Work tests — commit, rollback, shared session, optimistic locking."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from agent_eval_domain.agent_integration.adapter import Adapter, AdapterVersion
from agent_eval_domain.agent_integration.agent import Agent, AgentVersion
from agent_eval_domain.common.errors import NotFoundError
from agent_eval_domain.common.ids import (
    AdapterId,
    AdapterVersionId,
    AgentId,
    AgentVersionId,
    CaseId,
    CaseVersionId,
    GraderId,
    GraderVersionId,
    PlatformVersionId,
    ProjectId,
    PromptId,
    PromptVersionId,
    RunId,
)
from agent_eval_domain.evaluation_management.case import (
    CaseVersion,
    EvaluationCase,
    Prompt,
    PromptVersion,
    ReferenceRepositoryState,
)
from agent_eval_domain.evaluation_management.project import Project
from agent_eval_domain.execution.run import EvaluationRun, RunPins
from agent_eval_domain.execution.run_status import RunStatus
from agent_eval_domain.grading.grader import Grader, GraderFamily, GraderVersion
from agent_eval_domain.versioning.models import VersionNumber
from agent_eval_domain.versioning.status import VersionStatus
from agent_eval_infrastructure.database.base import Base
from agent_eval_infrastructure.database.engine import create_db_engine, dispose_engine
from agent_eval_infrastructure.database.models.execution.run import RunOrm
from agent_eval_infrastructure.database.session import create_session_factory
from agent_eval_infrastructure.unit_of_work import (
    SqlAlchemyUnitOfWork,
    SqlAlchemyUnitOfWorkFactory,
    UnitOfWorkStateError,
)
from sqlalchemy.orm.exc import StaleDataError

NOW = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def uow_factory() -> SqlAlchemyUnitOfWorkFactory:
    engine = create_db_engine(url="sqlite+pysqlite:///:memory:")
    import agent_eval_infrastructure.database.models  # noqa: F401

    Base.metadata.create_all(engine)
    factory = SqlAlchemyUnitOfWorkFactory(create_session_factory(engine))
    yield factory
    dispose_engine(engine)


def _project(project_id: str = "proj-1") -> Project:
    return Project(
        id=ProjectId(project_id),
        name="Demo",
        description="d",
        created_at=NOW,
        settings={},
    )


def _seed_run(uow: SqlAlchemyUnitOfWork) -> None:
    """Persist a minimal graph so a Run row exists for locking tests."""
    project = _project()
    uow.projects.save(project)

    grader = Grader(
        id=GraderId("grader-1"),
        name="pytest",
        family=GraderFamily.OBJECTIVE,
        created_at=NOW,
    )
    gv = GraderVersion(
        id=GraderVersionId("grader-v1"),
        grader_id=grader.id,
        version_number=VersionNumber(1),
        status=VersionStatus.ACTIVE,
        label="v1",
        specification="spec",
        created_at=NOW,
        predecessor_version_id=None,
    )
    grader._versions = [gv]  # noqa: SLF001
    uow.graders.save(grader)

    prompt = Prompt(id=PromptId("prompt-1"), case_id=CaseId("case-1"), created_at=NOW)
    pv = PromptVersion(
        id=PromptVersionId("prompt-v1"),
        prompt_id=prompt.id,
        version_number=VersionNumber(1),
        status=VersionStatus.ACTIVE,
        content="do it",
        predecessor_version_id=None,
        created_at=NOW,
    )
    prompt._versions = [pv]  # noqa: SLF001
    case = EvaluationCase(
        id=CaseId("case-1"),
        project_id=project.id,
        name="c1",
        prompt=prompt,
        created_at=NOW,
    )
    cv = CaseVersion(
        id=CaseVersionId("case-v1"),
        case_id=case.id,
        version_number=VersionNumber(1),
        status=VersionStatus.ACTIVE,
        description="d",
        reference_repository=ReferenceRepositoryState(
            repository_url="https://example.com/r.git",
            commit_sha="abc",
        ),
        expected_checks=(),
        applicable_grader_ids=(grader.id,),
        prompt_version_id=pv.id,
        predecessor_version_id=None,
        created_at=NOW,
    )
    case._versions = [cv]  # noqa: SLF001
    uow.cases.save(case)

    agent = Agent(id=AgentId("agent-1"), name="A", created_at=NOW)
    av = AgentVersion(
        id=AgentVersionId("agent-v1"),
        agent_id=agent.id,
        version_number=VersionNumber(1),
        status=VersionStatus.ACTIVE,
        label="v1",
        created_at=NOW,
        predecessor_version_id=None,
    )
    agent._versions = [av]  # noqa: SLF001
    uow.agents.save(agent)

    adapter = Adapter(
        id=AdapterId("adapter-1"),
        agent_id=agent.id,
        name="Ad",
        created_at=NOW,
    )
    adv = AdapterVersion(
        id=AdapterVersionId("adapter-v1"),
        adapter_id=adapter.id,
        version_number=VersionNumber(1),
        status=VersionStatus.ACTIVE,
        label="v1",
        created_at=NOW,
        predecessor_version_id=None,
    )
    adapter._versions = [adv]  # noqa: SLF001
    uow.adapters.save(adapter)
    agent.adapter_id = adapter.id
    uow.agents.save(agent)

    run = EvaluationRun(
        id=RunId("run-1"),
        pins=RunPins(
            project_id=project.id,
            case_version_id=cv.id,
            prompt_version_id=pv.id,
            agent_version_id=av.id,
            adapter_version_id=adv.id,
            platform_version_id=PlatformVersionId("platform-v1"),
            grader_version_ids=(gv.id,),
        ),
        status=RunStatus.CREATED,
        created_at=NOW,
    )
    uow.runs.save(run)


def test_commit_persists_across_units_of_work(uow_factory) -> None:
    with uow_factory() as uow:
        uow.projects.save(_project())
        uow.commit()

    with uow_factory() as uow:
        loaded = uow.projects.get(ProjectId("proj-1"))
        assert loaded.name == "Demo"


def test_rollback_discards_uncommitted_changes(uow_factory) -> None:
    with uow_factory() as uow:
        uow.projects.save(_project())
        uow.rollback()

    with uow_factory() as uow:
        with pytest.raises(NotFoundError):
            uow.projects.get(ProjectId("proj-1"))


def test_exit_without_commit_rolls_back(uow_factory) -> None:
    with uow_factory() as uow:
        uow.projects.save(_project())

    with uow_factory() as uow:
        with pytest.raises(NotFoundError):
            uow.projects.get(ProjectId("proj-1"))


def test_rollback_after_exception(uow_factory) -> None:
    with pytest.raises(RuntimeError, match="boom"):
        with uow_factory() as uow:
            uow.projects.save(_project())
            raise RuntimeError("boom")

    with uow_factory() as uow:
        with pytest.raises(NotFoundError):
            uow.projects.get(ProjectId("proj-1"))


def test_repositories_share_exact_same_session(uow_factory) -> None:
    with uow_factory() as uow:
        session = uow.session
        assert uow.projects.session is session  # type: ignore[attr-defined]
        assert uow.suites.session is session  # type: ignore[attr-defined]
        assert uow.cases.session is session  # type: ignore[attr-defined]
        assert uow.agents.session is session  # type: ignore[attr-defined]
        assert uow.adapters.session is session  # type: ignore[attr-defined]
        assert uow.graders.session is session  # type: ignore[attr-defined]
        assert uow.runs.session is session  # type: ignore[attr-defined]


def test_transaction_isolation_uncommitted_not_visible(uow_factory) -> None:
    with uow_factory() as uow_a:
        uow_a.projects.save(_project("proj-iso"))
        uow_a.rollback()

    with uow_factory() as uow_b:
        with pytest.raises(NotFoundError):
            uow_b.projects.get(ProjectId("proj-iso"))


def test_inactive_uow_raises(uow_factory) -> None:
    uow = uow_factory()
    with pytest.raises(UnitOfWorkStateError):
        _ = uow.projects


def test_nested_enter_rejected(uow_factory) -> None:
    with uow_factory() as uow:
        with pytest.raises(UnitOfWorkStateError):
            uow.__enter__()


def test_optimistic_locking_propagates_on_commit(tmp_path) -> None:
    """Concurrent Run status updates must raise StaleDataError via UoW.commit.

    File-backed SQLite gives each session a real connection (StaticPool
    ``:memory:`` cannot isolate concurrent transactions).
    """
    db_path = tmp_path / "uow.sqlite"
    engine = create_db_engine(url=f"sqlite+pysqlite:///{db_path}")
    import agent_eval_infrastructure.database.models  # noqa: F401

    Base.metadata.create_all(engine)
    factory = SqlAlchemyUnitOfWorkFactory(create_session_factory(engine))
    try:
        with factory() as uow:
            _seed_run(uow)
            uow.commit()

        with factory() as uow_a, factory() as uow_b:
            row_a = uow_a.session.get(RunOrm, "run-1")
            row_b = uow_b.session.get(RunOrm, "run-1")
            assert row_a is not None and row_b is not None
            assert row_a.lock_version == row_b.lock_version == 1

            row_a.status = RunStatus.QUEUED.value
            uow_a.commit()
            assert row_a.lock_version == 2

            row_b.status = RunStatus.RUNNING.value
            with pytest.raises(StaleDataError):
                uow_b.commit()
    finally:
        dispose_engine(engine)


def test_factory_returns_fresh_uow_each_call(uow_factory) -> None:
    first = uow_factory()
    second = uow_factory()
    assert first is not second
    assert isinstance(first, SqlAlchemyUnitOfWork)


def test_begin_nested_savepoint_helper(uow_factory) -> None:
    """SAVEPOINT helper exists for rare call sites; not part of the UoW port."""
    from agent_eval_infrastructure.transactions import begin_nested

    with uow_factory() as uow:
        uow.projects.save(_project("proj-outer"))
        uow.session.flush()
        try:
            with begin_nested(uow.session):
                uow.projects.save(_project("proj-inner"))
                uow.session.flush()
                raise RuntimeError("undo savepoint")
        except RuntimeError:
            pass
        uow.commit()

    with uow_factory() as uow:
        assert uow.projects.get(ProjectId("proj-outer")).name == "Demo"
        with pytest.raises(NotFoundError):
            uow.projects.get(ProjectId("proj-inner"))
