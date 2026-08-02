"""SQLAlchemy persistence foundation.

Engine, sessions, declarative Base, naming conventions, ORM models, and
repository base classes. Persistence models stay inside Infrastructure —
Domain never imports them (Data Mapper / Backend Architecture §5).
"""

from agent_eval_infrastructure.database.base import Base, metadata
from agent_eval_infrastructure.database.config import DatabaseSettings
from agent_eval_infrastructure.database.engine import (
    create_db_engine,
    dispose_engine,
)
from agent_eval_infrastructure.database.session import (
    SessionFactory,
    create_session_factory,
    session_scope,
)

__all__ = [
    "Base",
    "DatabaseSettings",
    "SessionFactory",
    "create_db_engine",
    "create_session_factory",
    "dispose_engine",
    "metadata",
    "session_scope",
]
