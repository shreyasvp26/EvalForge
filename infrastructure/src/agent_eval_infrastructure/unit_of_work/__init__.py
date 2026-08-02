"""Transactional Unit of Work implementing the Application port.

Coordinates repository lifetime, commit, and rollback. Does not dispatch
domain events (Application owns commit → dispatch per ADR-0002).
"""

from agent_eval_infrastructure.unit_of_work.sqlalchemy import (
    SqlAlchemyUnitOfWork,
    SqlAlchemyUnitOfWorkFactory,
    UnitOfWorkStateError,
)

__all__ = [
    "SqlAlchemyUnitOfWork",
    "SqlAlchemyUnitOfWorkFactory",
    "UnitOfWorkStateError",
]
