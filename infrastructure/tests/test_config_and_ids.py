"""ID generator and configuration loading tests."""

from __future__ import annotations

import uuid

from agent_eval_infrastructure.config import (
    InfrastructureSettings,
    load_infrastructure_settings,
)
from agent_eval_infrastructure.database.config import DatabaseSettings
from agent_eval_infrastructure.ids import UuidIdGenerator


def test_uuid_id_generator_produces_opaque_uuid_strings() -> None:
    gen = UuidIdGenerator()
    first = gen.new_id()
    second = gen.new_id()
    assert first != second
    uuid.UUID(first)
    uuid.UUID(second)


def test_infrastructure_settings_defaults(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("OBJECT_STORAGE_BUCKET", raising=False)
    settings = InfrastructureSettings()
    assert "postgresql" in settings.database_url
    assert settings.redis_url.startswith("redis://")
    assert settings.object_storage_bucket == "evalforge-artifacts"


def test_infrastructure_settings_from_env(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://db/test")
    monkeypatch.setenv("REDIS_URL", "redis://redis:6379/1")
    monkeypatch.setenv("OBJECT_STORAGE_BUCKET", "my-bucket")
    monkeypatch.setenv("OBJECT_STORAGE_ENDPOINT_URL", "http://minio:9000")
    settings = load_infrastructure_settings()
    assert settings.database_url.endswith("/test")
    assert settings.redis_url.endswith("/1")
    assert settings.object_storage_bucket == "my-bucket"
    assert settings.object_storage_endpoint_url == "http://minio:9000"


def test_to_database_settings_projection(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://db/proj")
    monkeypatch.setenv("DATABASE_POOL_SIZE", "7")
    settings = load_infrastructure_settings()
    db = settings.to_database_settings()
    assert isinstance(db, DatabaseSettings)
    assert db.database_url.endswith("/proj")
    assert db.pool_size == 7
