"""Authentication boundary — verify identity at the API Layer only.

Authorization (Project-scoped policy) remains an Application concern
(Backend Architecture §4 / §8, REST Authentication / Authorization).
"""

from __future__ import annotations

from agent_eval_application.common.actor import Actor
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from agent_eval_api.config import ApiSettings


def authenticate_bearer(
    credentials: HTTPAuthorizationCredentials | None,
    settings: ApiSettings,
) -> Actor:
    """Validate the Bearer credential and return an Application ``Actor``.

    Current policy (dev boundary only):
    - Missing/invalid scheme → 401
    - Non-empty token accepted as Actor id when ``auth_dev_accept_bearer_as_actor_id``
    - Real JWT / opaque-token verification is TODO
    """
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid Authorization Bearer credential",
        )
    token = credentials.credentials.strip()
    if not token:
        raise HTTPException(status_code=401, detail="Empty Bearer token")

    if settings.auth_dev_accept_bearer_as_actor_id:
        return Actor(id=token)

    raise HTTPException(
        status_code=401,
        detail="Token verification is not configured",
    )
