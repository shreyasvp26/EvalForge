"""EvalForge Domain Layer.

Technology-independent business model. Depends only on ``agent_eval_shared``
for cross-cutting error base types — never on application, infrastructure,
API, workers, adapters, or graders.
"""

from agent_eval_domain.common.errors import (
    DomainError,
    InvalidStateTransition,
    InvariantViolation,
    NotFoundError,
)

__all__ = [
    "DomainError",
    "InvariantViolation",
    "InvalidStateTransition",
    "NotFoundError",
]
