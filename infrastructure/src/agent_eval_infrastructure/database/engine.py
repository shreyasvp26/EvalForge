"""SQLAlchemy Engine factory and lifecycle."""

from __future__ import annotations

from sqlalchemy import Engine, create_engine
from sqlalchemy.pool import StaticPool

from agent_eval_infrastructure.database.config import DatabaseSettings


def create_db_engine(
    settings: DatabaseSettings | None = None,
    *,
    url: str | None = None,
) -> Engine:
    """Create a configured SQLAlchemy Engine.

    Prefer ``settings`` from the environment. ``url`` overrides are intended
    for tests (e.g. in-memory SQLite) without mutating process env.

    Sync Engine only — Backend Architecture does not require async ORM for
    the Control Plane; workers and API share the same session style.
    """
    cfg = settings or DatabaseSettings()
    engine_url = url if url is not None else cfg.database_url

    if engine_url.startswith("sqlite"):
        return create_engine(
            engine_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=cfg.echo_sql,
            future=True,
        )

    return create_engine(
        engine_url,
        pool_size=cfg.pool_size,
        max_overflow=cfg.max_overflow,
        pool_timeout=cfg.pool_timeout_seconds,
        pool_pre_ping=cfg.pool_pre_ping,
        echo=cfg.echo_sql,
        future=True,
    )


def dispose_engine(engine: Engine) -> None:
    """Release all pooled connections. Call at process shutdown."""
    engine.dispose()
