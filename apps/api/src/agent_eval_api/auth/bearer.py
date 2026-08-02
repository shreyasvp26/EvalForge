"""Authentication boundary — verify identity at the API Layer only.

Authorization (Project-scoped policy) remains an Application concern
(Backend Architecture §4 / §8, REST Authentication / Authorization).
"""

from __future__ import annotations

from agent_eval_application.common.actor import Actor
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from agent_eval_api.auth.jwt import JwtAuthenticationError, actor_from_access_token
from agent_eval_api.config import ApiSettings


def authenticate_bearer(
    credentials: HTTPAuthorizationCredentials | None,
    settings: ApiSettings,
) -> Actor:
    """Validate the Bearer credential and return an Application ``Actor``.

    Production path: JWT verification (``sub`` → Actor id).
    Optional escape hatch: ``AUTH_DEV_ACCEPT_BEARER_AS_ACTOR_ID`` treats the
    raw token string as the Actor id (local scripts only).
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

    try:
        return actor_from_access_token(token, settings)
    except JwtAuthenticationError as exc:
        raise HTTPException(status_code=401, detail=exc.message) from exc
