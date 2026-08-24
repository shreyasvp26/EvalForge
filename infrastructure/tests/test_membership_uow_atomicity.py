"""SQLAlchemy membership upsert joins the active Unit of Work transaction."""

from __future__ import annotations

import agent_eval_infrastructure.database.models  # noqa: F401
import pytest
from agent_eval_domain.common.ids import ProjectId
from agent_eval_domain.evaluation_management.project import Project
from agent_eval_infrastructure.auth import ProjectRole, SqlAlchemyMembershipStore
from agent_eval_infrastructure.auth.membership import ProjectMembershipOrm
from agent_eval_infrastructure.database.base import Base
from agent_eval_infrastructure.database.engine import create_db_engine, dispose_engine
from agent_eval_infrastructure.database.models.evaluation_management.project import (
    ProjectOrm,
)
from agent_eval_infrastructure.database.session import create_session_factory
from agent_eval_infrastructure.unit_of_work import SqlAlchemyUnitOfWorkFactory
from sqlalchemy import select


@pytest.fixture
def session_factory():
    engine = create_db_engine(url="sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    try:
        yield factory
    finally:
        dispose_engine(engine)


def test_owner_grant_rolls_back_with_project(session_factory) -> None:
    uow_factory = SqlAlchemyUnitOfWorkFactory(session_factory)
    memberships = SqlAlchemyMembershipStore(session_factory)
    project_id = ProjectId("proj-rollback")

    with pytest.raises(RuntimeError, match="boom"):
        with uow_factory() as uow:
            project = Project.create(
                project_id=project_id,
                name="Temp",
                description="",
            )
            uow.projects.save(project)
            memberships.upsert(
                actor_id="actor-1",
                project_id=project_id.value,
                role=ProjectRole.OWNER,
            )
            raise RuntimeError("boom")

    with session_factory() as session:
        assert session.execute(select(ProjectOrm)).scalars().all() == []
        assert session.execute(select(ProjectMembershipOrm)).scalars().all() == []


def test_owner_grant_commits_with_project(session_factory) -> None:
    uow_factory = SqlAlchemyUnitOfWorkFactory(session_factory)
    memberships = SqlAlchemyMembershipStore(session_factory)
    project_id = ProjectId("proj-ok")

    with uow_factory() as uow:
        project = Project.create(
            project_id=project_id,
            name="Owned",
            description="",
        )
        uow.projects.save(project)
        memberships.upsert(
            actor_id="actor-1",
            project_id=project_id.value,
            role=ProjectRole.OWNER,
        )
        uow.commit()

    assert (
        memberships.get_role(actor_id="actor-1", project_id=project_id.value)
        is ProjectRole.OWNER
    )
