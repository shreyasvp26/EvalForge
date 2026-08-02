"""Request timing middleware — record duration for structured logging."""

from __future__ import annotations

import time

from starlette.types import ASGIApp, Message, Receive, Scope, Send

REQUEST_DURATION_MS_HEADER = "X-Request-Duration-Ms"


class RequestTimingMiddleware:
    """Measure wall-clock request duration and expose it on the response."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        started = time.perf_counter()

        async def send_with_timing(message: Message) -> None:
            if message["type"] == "http.response.start":
                elapsed_ms = (time.perf_counter() - started) * 1000.0
                scope["evalforge_request_duration_ms"] = elapsed_ms
                raw_headers = list(message.get("headers", []))
                raw_headers.append(
                    (
                        REQUEST_DURATION_MS_HEADER.lower().encode("latin-1"),
                        f"{elapsed_ms:.2f}".encode("latin-1"),
                    )
                )
                message = {**message, "headers": raw_headers}
            await send(message)

        await self.app(scope, receive, send_with_timing)
