"""Repository base classes — session binding only.

Concrete ``get`` / ``save`` / query methods live in sibling modules.
This base exists so every adapter shares one session-lifetime pattern without
embedding Domain logic.
"""

from __future__ import annotations

from sqlalchemy.orm import Session


class SqlAlchemyRepository:
    """Base for Infrastructure repository adapters.

    Holds the active SQLAlchemy ``Session`` supplied by the Unit of Work
    (Phase 4). Subclasses must not open or commit their own sessions.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    @property
    def session(self) -> Session:
        return self._session
