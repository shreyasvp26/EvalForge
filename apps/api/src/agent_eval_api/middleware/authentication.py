"""ASGI authentication middleware — Bearer JWT → request actor.

Health / docs remain unauthenticated. When an Authorization header is
present it is verified immediately; missing credentials are left to the
``ActorDep`` dependency (or test overrides).
"""

from __future__ import annotations

from fastapi.security import HTTPAuthorizationCredentials
from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from agent_eval_api.auth.bearer import authenticate_bearer
from agent_eval_api.config import ApiSettings
from agent_eval_api.errors import error_body

UNAUTHENTICATED_PREFIXES = ("/health/",)
UNAUTHENTICATED_PATHS = frozenset(
    {
        "/docs",
        "/redoc",
        "/openapi.json",
        "/metrics",
        "/v1/auth/login",
        "/v1/auth/providers",
        "/v1/auth/oauth/exchange",
        "/v1/auth/google/authorize",
        "/v1/auth/google/callback",
        "/v1/auth/github/authorize",
        "/v1/auth/github/callback",
    }
)


class AuthenticationMiddleware:
    """Verify Bearer credentials early and attach ``Actor`` to the request."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path") or ""
        if _is_public(path):
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        auth_header = headers.get("authorization")
        if not auth_header:
            await self.app(scope, receive, send)
            return

        settings = _resolve_settings(scope)
        if settings is None:
            await self.app(scope, receive, send)
            return

        credentials = _parse_authorization(auth_header)
        try:
            actor = authenticate_bearer(credentials, settings)
        except Exception as exc:  # noqa: BLE001
            from fastapi import HTTPException

            if isinstance(exc, HTTPException):
                response = JSONResponse(
                    status_code=exc.status_code,
                    content=error_body(
                        code="UNAUTHENTICATED",
                        message=str(exc.detail),
                        retryable=False,
                    ),
                    headers={"WWW-Authenticate": "Bearer"},
                )
                await response(scope, receive, send)
                return
            raise

        if "state" not in scope or not isinstance(scope["state"], dict):
            scope["state"] = {}
        scope["state"]["actor"] = actor
        scope["evalforge_actor"] = actor
        await self.app(scope, receive, send)


def _is_public(path: str) -> bool:
    if path in UNAUTHENTICATED_PATHS:
        return True
    return any(path.startswith(prefix) for prefix in UNAUTHENTICATED_PREFIXES)


def _resolve_settings(scope: Scope) -> ApiSettings | None:
    app = scope.get("app")
    if app is None:
        return None
    container = getattr(getattr(app, "state", None), "container", None)
    if container is not None:
        return container.settings
    return getattr(getattr(app, "state", None), "settings", None)


def _parse_authorization(
    header: str | None,
) -> HTTPAuthorizationCredentials | None:
    if not header:
        return None
    parts = header.split(" ", 1)
    if len(parts) != 2:
        return HTTPAuthorizationCredentials(scheme=parts[0], credentials="")
    return HTTPAuthorizationCredentials(scheme=parts[0], credentials=parts[1])
