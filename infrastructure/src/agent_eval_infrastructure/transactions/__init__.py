"""Low-level transaction helpers.

Application owns transaction *boundaries* via Unit of Work. Nested SAVEPOINTs
are not part of the Application ``UnitOfWork`` port (Backend Architecture /
ADR-0002 open one UoW per use case). This helper remains for rare Infrastructure
call sites that need a SAVEPOINT inside an already-open session.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.orm import Session


@contextmanager
def begin_nested(session: Session) -> Iterator[Session]:
    """Open a SAVEPOINT nested transaction when the outer session is active."""
    with session.begin_nested():
        yield session
