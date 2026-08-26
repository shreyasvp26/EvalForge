"""Alembic migration tests — upgrade / downgrade against SQLite."""

from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

INFRA_ROOT = Path(__file__).resolve().parents[1]
ALEMBIC_INI = INFRA_ROOT / "alembic.ini"

EXPECTED_TABLES = {
    "projects",
    "project_memberships",
    "users",
    "oauth_identities",
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
    "platforms",
    "platform_versions",
    "runs",
    "execution_events",
    "artifacts",
    "scores",
    "suite_compositions",
    "case_grader_declarations",
    "audit_logs",
    "provider_connections",
    "alembic_version",
}


@pytest.fixture
def alembic_cfg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Config:
    db_path = tmp_path / "migrations.db"
    url = f"sqlite+pysqlite:///{db_path}"
    monkeypatch.setenv("DATABASE_URL", url)
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(INFRA_ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def test_upgrade_head_creates_schema(alembic_cfg: Config) -> None:
    command.upgrade(alembic_cfg, "head")
    url = alembic_cfg.get_main_option("sqlalchemy.url")
    assert url is not None
    engine = create_engine(url)
    try:
        tables = set(inspect(engine).get_table_names())
        assert EXPECTED_TABLES.issubset(tables)
        with engine.connect() as conn:
            version = conn.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar()
        assert version == "b2c3d4e5f6a7"
    finally:
        engine.dispose()


def test_downgrade_base_removes_schema(alembic_cfg: Config) -> None:
    command.upgrade(alembic_cfg, "head")
    command.downgrade(alembic_cfg, "base")
    url = alembic_cfg.get_main_option("sqlalchemy.url")
    assert url is not None
    engine = create_engine(url)
    try:
        tables = set(inspect(engine).get_table_names())
        # Alembic version table may remain empty or be dropped depending on
        # dialect; business tables must be gone.
        assert not (EXPECTED_TABLES - {"alembic_version"}) & tables
    finally:
        engine.dispose()


def test_upgrade_after_downgrade_is_idempotent(alembic_cfg: Config) -> None:
    command.upgrade(alembic_cfg, "head")
    command.downgrade(alembic_cfg, "base")
    command.upgrade(alembic_cfg, "head")
    url = alembic_cfg.get_main_option("sqlalchemy.url")
    assert url is not None
    engine = create_engine(url)
    try:
        tables = set(inspect(engine).get_table_names())
        assert EXPECTED_TABLES.issubset(tables)
    finally:
        engine.dispose()
