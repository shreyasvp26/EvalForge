"""Request metrics middleware — Prometheus HTTP counters / histograms."""

from __future__ import annotations

from agent_eval_shared.metrics import observe_http_request
from agent_eval_shared.tracing import start_span
from starlette.types import ASGIApp, Message, Receive, Scope, Send

_SKIP_PATHS = frozenset({"/metrics", "/health/live", "/health/ready"})


class RequestMetricsMiddleware:
    """Record structured HTTP request metrics after each response."""

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

        endpoint = _endpoint_label(scope, path)
        with start_span(
            "http.request",
            tracer_name="evalforge.api",
            attributes={
                "http.method": method,
                "http.route": endpoint,
                "http.target": path,
            },
        ):
            try:
                await self.app(scope, receive, send_wrapper)
            finally:
                if path not in _SKIP_PATHS:
                    duration_ms = scope.get("evalforge_request_duration_ms")
                    duration_s = (
                        float(duration_ms) / 1000.0
                        if isinstance(duration_ms, (int, float))
                        else 0.0
                    )
                    observe_http_request(
                        method=method,
                        endpoint=endpoint,
                        status_code=status_code,
                        duration_seconds=duration_s,
                    )


def _endpoint_label(scope: Scope, path: str) -> str:
    route = scope.get("route")
    template = getattr(route, "path", None)
    if isinstance(template, str) and template:
        return template
    return path
