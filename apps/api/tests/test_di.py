"""Dependency injection / composition root tests."""

from __future__ import annotations

from agent_eval_api.auth.authorization import AllowAllAuthorization
from agent_eval_api.auth.rbac import ProjectRbacAuthorization
from agent_eval_api.composition import (
    ApplicationServices,
    build_api_container,
    build_application_services,
)
from agent_eval_api.dependencies import get_actor
from agent_eval_api.main import create_app
from agent_eval_application.common.actor import Actor
from agent_eval_domain.common.ids import ProjectId
from agent_eval_infrastructure import RuntimeProfile, build_infrastructure
from agent_eval_infrastructure.auth import (
    InMemoryIdentityStore,
    InMemoryMembershipStore,
)
from api_fakes import FakeContainer, mock_services
from fastapi.testclient import TestClient


def test_build_application_services_from_memory_infra() -> None:
    infra = build_infrastructure(profile=RuntimeProfile.MEMORY)
    try:
        auth = AllowAllAuthorization()
        identity = InMemoryIdentityStore()
        services = build_application_services(infra, auth, identity)
        assert isinstance(services, ApplicationServices)
        assert services.login is not None
        assert services.get_current_user is not None
        assert services.create_project is not None
        assert services.create_run is not None
        auth.ensure_can_create_project(Actor(id="actor-1"))
        auth.ensure_can_access_project(Actor(id="actor-1"), ProjectId("p1"))
        auth.ensure_can_manage_project(Actor(id="actor-1"), ProjectId("p1"))
    finally:
        infra.dispose()


def test_build_api_container_wires_services(settings) -> None:
    from agent_eval_infrastructure.config import InfrastructureSettings

    infra_settings = InfrastructureSettings(
        environment="test",
        database_url="sqlite+pysqlite:///:memory:",
    )
    container = build_api_container(
        settings=settings,
        infrastructure=build_infrastructure(
            settings=infra_settings,
            profile=RuntimeProfile.MEMORY,
        ),
    )
    try:
        assert container.settings is settings
        assert isinstance(container.services, ApplicationServices)
        assert isinstance(container.auth, ProjectRbacAuthorization)
        assert isinstance(container.memberships, InMemoryMembershipStore)
        assert isinstance(container.identity, InMemoryIdentityStore)
        checks = container.readiness_checks()
        assert checks["composition"] == "ok"
        assert checks["database"] == "ok"
    finally:
        container.dispose()


def test_dependency_overrides_actor(settings) -> None:
    services = mock_services()
    container = FakeContainer(services=services, settings=settings)
    app = create_app(container=container, settings=settings)
    app.dependency_overrides[get_actor] = lambda: Actor(id="override-actor")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/v1/system/info")
        assert response.status_code == 200
        assert response.json()["api_version"] == "v1"

    app.dependency_overrides.clear()
