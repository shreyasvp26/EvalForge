"""Session factory and connection lifecycle helpers.

Application owns *when* a unit of work starts/ends (Backend Architecture §8).
Infrastructure provides the Session factory that executes within that boundary.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

type SessionFactory = sessionmaker[Session]


def create_session_factory(engine: Engine) -> SessionFactory:
    """Bind a ``sessionmaker`` to ``engine`` with expire-on-commit disabled.

    ``expire_on_commit=False`` keeps loaded attributes usable after commit
    inside Application orchestration without implicit refreshes. Unit of Work
    (Phase 4) still controls commit/rollback explicitly.
    """
    return sessionmaker(
        bind=engine,
        class_=Session,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )


@contextmanager
def session_scope(factory: SessionFactory) -> Iterator[Session]:
    """Open a Session, yield it, commit on success, rollback on error, close.

    Thin lifecycle helper for scripts/tests. Production use cases should go
    through the Application Unit of Work (Phase 4), not this helper.
    """
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
