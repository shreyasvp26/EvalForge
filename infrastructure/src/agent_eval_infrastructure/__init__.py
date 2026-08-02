"""EvalForge Infrastructure Layer.

Concrete adapters for Domain repository Protocols and Application ports.
Depends on ``agent_eval_domain``, ``agent_eval_application``, and
``agent_eval_shared``. Contains no business logic — see Backend Architecture
§4 / §5 / §11.
"""

from agent_eval_infrastructure.config import (
    InfrastructureSettings,
    load_infrastructure_settings,
)
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
from agent_eval_infrastructure.dependency_injection import (
    InfrastructureContainer,
    RuntimeProfile,
    build_infrastructure,
)
from agent_eval_infrastructure.unit_of_work import (
    SqlAlchemyUnitOfWork,
    SqlAlchemyUnitOfWorkFactory,
)

__all__ = [
    "Base",
    "DatabaseSettings",
    "InfrastructureContainer",
    "InfrastructureSettings",
    "RuntimeProfile",
    "SessionFactory",
    "SqlAlchemyUnitOfWork",
    "SqlAlchemyUnitOfWorkFactory",
    "build_infrastructure",
    "create_db_engine",
    "create_session_factory",
    "dispose_engine",
    "load_infrastructure_settings",
    "metadata",
    "session_scope",
]
