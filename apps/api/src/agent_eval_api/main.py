"""FastAPI Control Plane application factory and process entrypoint."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from agent_eval_infrastructure import RuntimeProfile
from agent_eval_shared.log import configure_logging
from fastapi import FastAPI

from agent_eval_api.composition import ApiContainer, build_api_container
from agent_eval_api.config import ApiSettings, load_api_settings
from agent_eval_api.errors import register_exception_handlers
from agent_eval_api.middleware.correlation import CorrelationIdMiddleware
from agent_eval_api.routers import (
    adapters,
    agents,
    cases,
    graders,
    health,
    projects,
    prompts,
    runs,
    suites,
    system,
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
        app.state.container = active
        try:
            yield
        finally:
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
    )
    app.add_middleware(CorrelationIdMiddleware)
    register_exception_handlers(app)

    app.include_router(health.router)
    app.include_router(system.router)
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
