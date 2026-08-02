"""Alembic environment — uses Infrastructure ORM metadata and DatabaseSettings."""

from __future__ import annotations

from logging.config import fileConfig

# Import models so every table registers on Base.metadata.
import agent_eval_infrastructure.database.models  # noqa: F401
from agent_eval_infrastructure.database.base import Base
from agent_eval_infrastructure.database.config import DatabaseSettings
from alembic import context
from sqlalchemy import engine_from_config, pool

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    """Resolve DB URL from env (DATABASE_URL) with alembic.ini as fallback."""
    settings = DatabaseSettings()
    ini_url = config.get_main_option("sqlalchemy.url")
    # Prefer explicit env / settings; fall back to ini for offline tooling.
    if settings.database_url:
        return settings.database_url
    return ini_url or "postgresql+psycopg://localhost:5432/evalforge"


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (SQL script generation)."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live database connection."""
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
