"""EvalForge Infrastructure Layer.

Concrete adapters for Domain repository Protocols and Application ports.
Depends on ``agent_eval_domain``, ``agent_eval_application``, and
``agent_eval_shared``. Contains no business logic — see Backend Architecture
§4 / §5 / §11.
"""

from agent_eval_infrastructure.database import (
    Base,
    DatabaseSettings,
    SessionFactory,
    create_db_engine,
    create_session_factory,
    dispose_engine,
    metadata,
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
