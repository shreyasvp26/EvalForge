"""Unit tests for SQLAlchemy persistence foundation."""

from __future__ import annotations

import pytest
from agent_eval_infrastructure.database.base import Base, metadata
from agent_eval_infrastructure.database.config import DatabaseSettings
from agent_eval_infrastructure.database.engine import create_db_engine, dispose_engine
from agent_eval_infrastructure.database.naming import NAMING_CONVENTION
from agent_eval_infrastructure.database.session import (
    create_session_factory,
    session_scope,
)
from agent_eval_infrastructure.repositories.base import SqlAlchemyRepository
from sqlalchemy import inspect
from sqlalchemy.orm import Session


@pytest.fixture
def sqlite_engine():
    engine = create_db_engine(url="sqlite+pysqlite:///:memory:")
    # Import models so they register on Base.metadata before create_all.
    import agent_eval_infrastructure.database.models  # noqa: F401

    Base.metadata.create_all(engine)
    yield engine
    dispose_engine(engine)


def test_naming_convention_keys() -> None:
    assert set(NAMING_CONVENTION) == {"ix", "uq", "ck", "fk", "pk"}
    assert metadata.naming_convention == NAMING_CONVENTION


def test_database_settings_defaults() -> None:
    settings = DatabaseSettings()
    assert "postgresql" in settings.database_url
    assert settings.pool_size >= 1
    assert settings.pool_pre_ping is True


def test_create_engine_and_dispose(sqlite_engine) -> None:
    assert sqlite_engine is not None
    with sqlite_engine.connect() as conn:
        assert conn.execute(__import__("sqlalchemy").text("SELECT 1")).scalar() == 1


def test_session_factory_and_scope(sqlite_engine) -> None:
    factory = create_session_factory(sqlite_engine)
    with session_scope(factory) as session:
        assert isinstance(session, Session)
        assert session.get_bind() is sqlite_engine


def test_model_registration_on_metadata(sqlite_engine) -> None:
    import agent_eval_infrastructure.database.models as models

    table_names = set(metadata.tables)
    expected = {
        "projects",
        "suites",
        "suite_versions",
        "cases",
        "case_versions",
        "prompts",
        "prompt_versions",
        "agents",
        "agent_versions",
        "adapters",
        "adapter_versions",
        "graders",
        "grader_versions",
        "runs",
        "execution_events",
        "artifacts",
        "scores",
        "suite_compositions",
        "case_grader_declarations",
        "audit_logs",
    }
    assert expected.issubset(table_names)

    inspector = inspect(sqlite_engine)
    assert "projects" in inspector.get_table_names()
    assert "runs" in inspector.get_table_names()
    assert models.ProjectOrm.__tablename__ == "projects"
    assert models.RunOrm.__tablename__ == "runs"


def test_run_has_optimistic_lock_column(sqlite_engine) -> None:
    from agent_eval_infrastructure.database.models import RunOrm

    cols = {c.name for c in RunOrm.__table__.columns}
    assert "lock_version" in cols
    assert "status" in cols


def test_repository_base_binds_session(sqlite_engine) -> None:
    factory = create_session_factory(sqlite_engine)
    with session_scope(factory) as session:
        repo = SqlAlchemyRepository(session)
        assert repo.session is session
