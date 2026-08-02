"""Database configuration loaded from the environment.

Infrastructure owns configuration loading for persistence. Domain never
reads configuration (Backend Architecture §8).
"""

from __future__ import annotations

from agent_eval_shared.config import BaseSettings
from pydantic import Field
from pydantic_settings import SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """PostgreSQL connection and pool settings for the Infrastructure Layer."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
    )

    database_url: str = Field(
        default="postgresql+psycopg://localhost:5432/evalforge",
        validation_alias="DATABASE_URL",
        description="SQLAlchemy database URL (postgresql+psycopg://…).",
    )
    pool_size: int = Field(default=5, ge=1, validation_alias="DATABASE_POOL_SIZE")
    max_overflow: int = Field(
        default=10,
        ge=0,
        validation_alias="DATABASE_MAX_OVERFLOW",
    )
    pool_timeout_seconds: float = Field(
        default=30.0,
        gt=0,
        validation_alias="DATABASE_POOL_TIMEOUT_SECONDS",
    )
    pool_pre_ping: bool = Field(
        default=True,
        validation_alias="DATABASE_POOL_PRE_PING",
    )
    echo_sql: bool = Field(default=False, validation_alias="DATABASE_ECHO_SQL")
