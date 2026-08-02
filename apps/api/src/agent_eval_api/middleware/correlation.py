"""Correlation-ID middleware — attach identifiers at the API entry point."""

from __future__ import annotations

from agent_eval_shared.log import bind_context, clear_context
from agent_eval_shared.utils import create_correlation_id
from starlette.types import ASGIApp, Message, Receive, Scope, Send

CORRELATION_HEADER = "X-Correlation-ID"


class CorrelationIdMiddleware:
    """Pure ASGI middleware so exception handlers remain effective."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {
            k.decode("latin-1").lower(): v.decode("latin-1")
            for k, v in scope.get("headers", [])
        }
        incoming = headers.get(CORRELATION_HEADER.lower())
        correlation_id = incoming.strip() if incoming else create_correlation_id()
        clear_context()
        bind_context(correlation_id=correlation_id)

        async def send_with_correlation(message: Message) -> None:
            if message["type"] == "http.response.start":
                raw_headers = list(message.get("headers", []))
                raw_headers.append(
                    (
                        CORRELATION_HEADER.lower().encode("latin-1"),
                        correlation_id.encode("latin-1"),
                    )
                )
                message = {**message, "headers": raw_headers}
            await send(message)

        try:
            await self.app(scope, receive, send_with_correlation)
        finally:
            clear_context()
