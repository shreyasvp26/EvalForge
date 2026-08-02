"""Transport hardening middleware — rate limit, body size, security headers."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass, field

from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from agent_eval_api.errors import error_body

SECURITY_HEADERS: tuple[tuple[str, str], ...] = (
    ("X-Content-Type-Options", "nosniff"),
    ("X-Frame-Options", "DENY"),
    ("Referrer-Policy", "no-referrer"),
    ("Permissions-Policy", "geolocation=(), microphone=(), camera=()"),
    ("X-XSS-Protection", "0"),
)


class SecurityHeadersMiddleware:
    """Attach baseline security headers to every HTTP response."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                existing = {k.lower() for k, _ in headers}
                for name, value in SECURITY_HEADERS:
                    key = name.lower().encode("latin-1")
                    if key not in existing:
                        headers.append((key, value.encode("latin-1")))
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_headers)


class RequestSizeLimitMiddleware:
    """Reject requests whose Content-Length exceeds the configured maximum."""

    def __init__(self, app: ASGIApp, *, max_body_bytes: int) -> None:
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        content_length = headers.get("content-length")
        if content_length is not None:
            try:
                length = int(content_length)
            except ValueError:
                length = -1
            if length > self.max_body_bytes:
                response = JSONResponse(
                    status_code=413,
                    content=error_body(
                        code="PAYLOAD_TOO_LARGE",
                        message="Request body exceeds size limit",
                        details={"max_body_bytes": self.max_body_bytes},
                        retryable=False,
                    ),
                )
                await response(scope, receive, send)
                return

        await self.app(scope, receive, send)


@dataclass
class _Window:
    timestamps: deque[float] = field(default_factory=deque)


class RateLimitMiddleware:
    """Fixed-window rate limiter keyed by Actor id or client host."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        requests_per_minute: int,
        enabled: bool = True,
    ) -> None:
        self.app = app
        self.requests_per_minute = max(1, requests_per_minute)
        self.enabled = enabled
        self._windows: dict[str, _Window] = defaultdict(_Window)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not self.enabled:
            await self.app(scope, receive, send)
            return

        path = scope.get("path") or ""
        public = path.startswith("/health/") or path in {
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
        }
        if public:
            await self.app(scope, receive, send)
            return

        key = _client_key(scope)
        now = time.monotonic()
        window = self._windows[key]
        cutoff = now - 60.0
        while window.timestamps and window.timestamps[0] < cutoff:
            window.timestamps.popleft()

        if len(window.timestamps) >= self.requests_per_minute:
            response = JSONResponse(
                status_code=429,
                content=error_body(
                    code="RATE_LIMITED",
                    message="Too many requests",
                    details={"limit_per_minute": self.requests_per_minute},
                    retryable=True,
                ),
                headers={"Retry-After": "60"},
            )
            await response(scope, receive, send)
            return

        window.timestamps.append(now)
        await self.app(scope, receive, send)


def _client_key(scope: Scope) -> str:
    actor = scope.get("evalforge_actor")
    actor_id = getattr(actor, "id", None)
    if isinstance(actor_id, str) and actor_id:
        return f"actor:{actor_id}"
    state = scope.get("state")
    if isinstance(state, dict):
        state_actor = state.get("actor")
        state_id = getattr(state_actor, "id", None)
        if isinstance(state_id, str) and state_id:
            return f"actor:{state_id}"
    client = scope.get("client")
    if client and client[0]:
        return f"ip:{client[0]}"
    return "ip:unknown"
