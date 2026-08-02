"""Structured request logging middleware."""

from __future__ import annotations

from agent_eval_shared.log import get_logger
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = get_logger("agent_eval_api.request")


class RequestLoggingMiddleware:
    """Log method, path, status, and duration after each HTTP request."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "")
        path = scope.get("path", "")
        status_code = 500

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message.get("status", 500))
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration_ms = scope.get("evalforge_request_duration_ms")
            logger.info(
                "http_request",
                method=method,
                path=path,
                status_code=status_code,
                duration_ms=duration_ms,
            )
