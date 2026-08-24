"""Configuration validation — JWT secret and database footguns."""

from __future__ import annotations

import pytest
from agent_eval_api.config import ApiSettings
from agent_eval_infrastructure.config import InfrastructureSettings
from agent_eval_shared.config import find_repo_root, resolve_env_file
from agent_eval_shared.errors import ConfigurationError
from pydantic import ValidationError


def test_production_rejects_missing_jwt_secret() -> None:
    with pytest.raises((ValueError, ValidationError, ConfigurationError)):
        ApiSettings(
            environment="production",
            jwt_secret_key=None,
            auth_dev_accept_bearer_as_actor_id=False,
        )


def test_production_rejects_insecure_jwt_placeholder() -> None:
    with pytest.raises(ValueError, match="insecure placeholder"):
        ApiSettings(
            environment="production",
            jwt_secret_key="change-me-in-production",
            auth_dev_accept_bearer_as_actor_id=False,
        )


def test_production_rejects_short_jwt_secret() -> None:
    with pytest.raises(ValueError, match="at least 32"):
        ApiSettings(
            environment="production",
            jwt_secret_key="only-sixteen-chars",
            auth_dev_accept_bearer_as_actor_id=False,
        )


def test_development_accepts_explicit_long_secret() -> None:
    settings = ApiSettings(
        environment="development",
        jwt_secret_key="dev-only-evalforge-jwt-secret-change-me-32b",
        auth_dev_accept_bearer_as_actor_id=False,
    )
    assert settings.jwt_secret_key is not None
    assert len(settings.jwt_secret_key) >= 32


def test_development_rejects_sqlite_database() -> None:
    with pytest.raises(ValueError, match="PostgreSQL"):
        InfrastructureSettings(
            environment="development",
            database_url="sqlite+pysqlite:///:memory:",
        )


def test_rejects_tmp_evalforge_sqlite_even_in_test() -> None:
    with pytest.raises(ValueError, match="/tmp/evalforge"):
        InfrastructureSettings(
            environment="test",
            database_url="sqlite+pysqlite:////tmp/evalforge.db",
        )


def test_test_environment_allows_memory_sqlite() -> None:
    settings = InfrastructureSettings(
        environment="test",
        database_url="sqlite+pysqlite:///:memory:",
    )
    assert settings.database_url.startswith("sqlite")


def test_resolve_env_file_is_repo_rooted() -> None:
    root = find_repo_root()
    assert root is not None
    resolved = resolve_env_file()
    # May be None if no .env exists; when present it must live at repo root.
    if resolved is not None:
        assert resolved.startswith(str(root))
