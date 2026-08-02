"""FastAPI Control Plane application factory and process entrypoint.

Phase 6B: foundation (6A) plus versioned business resource routers over
Application use cases only.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from agent_eval_infrastructure import RuntimeProfile
from agent_eval_shared.log import configure_logging
from agent_eval_shared.metrics import configure_metrics
from agent_eval_shared.tracing import configure_tracing, shutdown_tracing
from fastapi import FastAPI
from starlette.middleware.gzip import GZipMiddleware

from agent_eval_api.composition import ApiContainer, build_api_container
from agent_eval_api.config import ApiSettings, load_api_settings
from agent_eval_api.errors import register_exception_handlers
from agent_eval_api.middleware.authentication import AuthenticationMiddleware
from agent_eval_api.middleware.correlation import CorrelationIdMiddleware
from agent_eval_api.middleware.hardening import (
    RateLimitMiddleware,
    RequestSizeLimitMiddleware,
    SecurityHeadersMiddleware,
)
from agent_eval_api.middleware.logging import RequestLoggingMiddleware
from agent_eval_api.middleware.metrics import RequestMetricsMiddleware
from agent_eval_api.middleware.timing import RequestTimingMiddleware
from agent_eval_api.routers import health, metrics, system, v1_root
from agent_eval_api.routers.v1 import (
    adapters,
    agents,
    auth,
    cases,
    graders,
    projects,
    prompts,
    runs,
    suites,
)


def create_app(
    *,
    container: ApiContainer | None = None,
    settings: ApiSettings | None = None,
) -> FastAPI:
    """Build the FastAPI application.

    When ``container`` is omitted, lifespan builds and disposes the composition
    root. Tests typically pass a pre-built container (often with MEMORY infra).
    """
    api_settings = settings or (
        container.settings if container else load_api_settings()
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        owned = container is None
        active = container or build_api_container(
            settings=api_settings,
            profile=(
                RuntimeProfile.MEMORY if api_settings.environment == "test" else None
            ),
        )
        configure_logging(
            level=api_settings.log_level,
            environment=api_settings.environment,
            service_name="evalforge-api",
        )
        configure_metrics(enabled=api_settings.metrics_enabled)
        configure_tracing(
            enabled=api_settings.tracing_enabled,
            service_name="evalforge-api",
            environment=api_settings.environment,
            otlp_endpoint=api_settings.otel_exporter_otlp_endpoint,
        )
        app.state.container = active
        try:
            yield
        finally:
            shutdown_tracing()
            if owned:
                active.dispose()
            app.state.container = None

    app = FastAPI(
        title=api_settings.api_title,
        version=api_settings.api_version,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        description=(
            "EvalForge Control Plane REST API (v1). "
            "Routers invoke Application use cases only — "
            "never repositories or Domain entities."
        ),
    )
    # Starlette applies middleware LIFO (last added = outermost):
    # correlation → body limit → rate limit → auth → security → gzip
    # → timing → logging → metrics (inner).
    app.add_middleware(RequestMetricsMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RequestTimingMiddleware)
    app.add_middleware(GZipMiddleware, minimum_size=api_settings.gzip_minimum_size)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(AuthenticationMiddleware)
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=api_settings.rate_limit_per_minute,
        enabled=api_settings.rate_limit_enabled,
    )
    app.add_middleware(
        RequestSizeLimitMiddleware,
        max_body_bytes=api_settings.max_request_body_bytes,
    )
    app.add_middleware(CorrelationIdMiddleware)
    register_exception_handlers(app)

    app.include_router(health.router)
    app.include_router(metrics.router)
    app.include_router(v1_root.router)
    app.include_router(system.router)
    app.include_router(auth.router)
    app.include_router(projects.router)
    app.include_router(suites.router)
    app.include_router(cases.router)
    app.include_router(prompts.router)
    app.include_router(agents.router)
    app.include_router(adapters.router)
    app.include_router(graders.router)
    app.include_router(runs.router)

    return app


def run() -> None:
    """CLI entry: ``evalforge-api`` / ``python -m agent_eval_api.main``."""
    import uvicorn

    settings = load_api_settings()
    uvicorn.run(
        "agent_eval_api.main:create_app",
        factory=True,
        host=settings.api_host,
        port=settings.api_port,
    )


if __name__ == "__main__":
    run()
