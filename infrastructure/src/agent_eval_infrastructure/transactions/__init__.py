"""Low-level transaction helpers shared by sessions and (later) Unit of Work.

Application decides transaction *boundaries*; Infrastructure executes them.
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
