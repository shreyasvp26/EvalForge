"""JWT token parsing and verification (API Layer only)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from agent_eval_application.common.actor import Actor

from agent_eval_api.config import ApiSettings


class JwtAuthenticationError(Exception):
    """Invalid or unusable JWT — mapped to HTTP 401 by the auth boundary."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


@dataclass(frozen=True, slots=True)
class ParsedAccessToken:
    """Claims extracted after successful verification."""

    subject: str
    claims: dict[str, Any]


def issue_access_token(
    actor_id: str,
    settings: ApiSettings,
    *,
    expires_seconds: int = 3600,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Mint a signed access token (tests / local tooling — not an OAuth server)."""
    if not settings.jwt_secret_key:
        raise JwtAuthenticationError("JWT_SECRET_KEY is not configured")
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": actor_id,
        "iat": now,
        "exp": now + timedelta(seconds=expires_seconds),
    }
    if settings.jwt_issuer:
        payload["iss"] = settings.jwt_issuer
    if settings.jwt_audience:
        payload["aud"] = settings.jwt_audience
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def parse_access_token(token: str, settings: ApiSettings) -> ParsedAccessToken:
    """Verify signature / expiry and return the parsed token."""
    if not settings.jwt_secret_key:
        raise JwtAuthenticationError("JWT_SECRET_KEY is not configured")
    options: dict[str, bool] = {"require": ["exp", "sub"]}
    decode_kwargs: dict[str, Any] = {
        "algorithms": [settings.jwt_algorithm],
        "options": options,
    }
    if settings.jwt_issuer:
        decode_kwargs["issuer"] = settings.jwt_issuer
    if settings.jwt_audience:
        decode_kwargs["audience"] = settings.jwt_audience
    try:
        claims = jwt.decode(token, settings.jwt_secret_key, **decode_kwargs)
    except jwt.ExpiredSignatureError as exc:
        raise JwtAuthenticationError("Token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise JwtAuthenticationError(f"Invalid token: {exc}") from exc

    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject.strip():
        raise JwtAuthenticationError("Token subject (sub) is missing")
    return ParsedAccessToken(subject=subject.strip(), claims=dict(claims))


def actor_from_access_token(token: str, settings: ApiSettings) -> Actor:
    """Verify a JWT and map ``sub`` to an Application ``Actor``."""
    parsed = parse_access_token(token, settings)
    return Actor(id=parsed.subject)
