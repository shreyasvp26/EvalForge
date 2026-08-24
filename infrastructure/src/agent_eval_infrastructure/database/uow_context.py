"""Bind the active Unit of Work session for adapters that must join it.

Membership / identity stores normally open their own short-lived sessions.
When called from inside ``SqlAlchemyUnitOfWork``, they must participate in
the same transaction so Application commits stay atomic.
"""

from __future__ import annotations

from contextvars import ContextVar, Token

from sqlalchemy.orm import Session

_active_uow_session: ContextVar[Session | None] = ContextVar(
    "evalforge_active_uow_session",
    default=None,
)


def set_active_uow_session(session: Session) -> Token[Session | None]:
    return _active_uow_session.set(session)


def reset_active_uow_session(token: Token[Session | None]) -> None:
    _active_uow_session.reset(token)


def get_active_uow_session() -> Session | None:
    return _active_uow_session.get()
