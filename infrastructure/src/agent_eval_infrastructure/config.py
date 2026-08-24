"""Infrastructure-wide settings loaded via ``agent_eval_shared.config``.

No direct ``os.environ`` access — all values flow through pydantic-settings
(Backend Architecture §8 / development guide).
"""

from __future__ import annotations

from agent_eval_shared.config import BaseSettings, load_settings, resolve_env_file
from pydantic import Field, model_validator
from pydantic_settings import SettingsConfigDict

from agent_eval_infrastructure.database.config import DatabaseSettings


class InfrastructureSettings(BaseSettings):
    """Concrete Infrastructure configuration (database, Redis, object storage)."""

    model_config = SettingsConfigDict(
        env_file=resolve_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
    )

    # --- Database (mirrors DatabaseSettings; single env source of truth) ---
    database_url: str = Field(
        default="postgresql+psycopg://localhost:5432/evalforge",
        validation_alias="DATABASE_URL",
    )
    database_pool_size: int = Field(
        default=5, ge=1, validation_alias="DATABASE_POOL_SIZE"
    )
    database_max_overflow: int = Field(
        default=10, ge=0, validation_alias="DATABASE_MAX_OVERFLOW"
    )
    database_pool_timeout_seconds: float = Field(
        default=30.0, gt=0, validation_alias="DATABASE_POOL_TIMEOUT_SECONDS"
    )
    database_pool_pre_ping: bool = Field(
        default=True, validation_alias="DATABASE_POOL_PRE_PING"
    )
    database_echo_sql: bool = Field(default=False, validation_alias="DATABASE_ECHO_SQL")

    # --- Redis / run queue ---
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        validation_alias="REDIS_URL",
        description="Redis URL for the run queue (and optional idempotency).",
    )
    run_queue_key_prefix: str = Field(
        default="evalforge:runs",
        validation_alias="RUN_QUEUE_KEY_PREFIX",
    )
    run_queue_claim_timeout_seconds: float = Field(
        default=5.0,
        gt=0,
        validation_alias="RUN_QUEUE_CLAIM_TIMEOUT_SECONDS",
    )

    # --- Object storage (S3-compatible; endpoint_url enables MinIO/R2/etc.) ---
    object_storage_endpoint_url: str | None = Field(
        default=None,
        validation_alias="OBJECT_STORAGE_ENDPOINT_URL",
        description="S3-compatible API endpoint. None uses the provider default.",
    )
    object_storage_access_key: str = Field(
        default="minioadmin",
        validation_alias="OBJECT_STORAGE_ACCESS_KEY",
    )
    object_storage_secret_key: str = Field(
        default="minioadmin",
        validation_alias="OBJECT_STORAGE_SECRET_KEY",
    )
    object_storage_bucket: str = Field(
        default="evalforge-artifacts",
        validation_alias="OBJECT_STORAGE_BUCKET",
    )
    object_storage_region: str = Field(
        default="us-east-1",
        validation_alias="OBJECT_STORAGE_REGION",
    )
    object_storage_force_path_style: bool = Field(
        default=True,
        validation_alias="OBJECT_STORAGE_FORCE_PATH_STYLE",
        description="Path-style addressing for MinIO and many S3-compatible stores.",
    )

    @model_validator(mode="after")
    def _reject_misleading_database_urls(self) -> InfrastructureSettings:
        """Fail fast on configs that look partially working but are unsafe."""
        url = self.database_url.strip()
        lowered = url.lower()
        is_sqlite = lowered.startswith("sqlite")

        if "/tmp/evalforge" in lowered:
            raise ValueError(
                "DATABASE_URL points at /tmp/evalforge*.db — this commonly pairs "
                "MEMORY identity (ENVIRONMENT=test) with an empty SQLite file for "
                "domain APIs. Use PostgreSQL for local development (see .env.example)."
            )

        if self.environment in ("development", "production") and is_sqlite:
            raise ValueError(
                f"DATABASE_URL must be PostgreSQL when ENVIRONMENT={self.environment}; "
                "SQLite is only allowed for ENVIRONMENT=test "
                "(typically sqlite+pysqlite:///:memory:)."
            )

        return self

    def to_database_settings(self) -> DatabaseSettings:
        """Project nested DB fields into the existing DatabaseSettings object."""
        return DatabaseSettings(
            database_url=self.database_url,
            pool_size=self.database_pool_size,
            max_overflow=self.database_max_overflow,
            pool_timeout_seconds=self.database_pool_timeout_seconds,
            pool_pre_ping=self.database_pool_pre_ping,
            echo_sql=self.database_echo_sql,
        )


def load_infrastructure_settings() -> InfrastructureSettings:
    """Load and validate Infrastructure settings from the environment."""
    return load_settings(InfrastructureSettings)
