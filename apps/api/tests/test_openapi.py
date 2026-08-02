"""OpenAPI generation and dependency override tests."""

from __future__ import annotations

from agent_eval_api.dependencies import get_actor, get_services
from agent_eval_api.main import create_app
from agent_eval_application.common.actor import Actor
from api_fakes import FakeContainer, mock_services, sample_project
from fastapi.testclient import TestClient


def test_openapi_generated(client) -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    spec = response.json()
    assert spec["info"]["title"]
    paths = spec["paths"]
    assert "/health/live" in paths
    assert "/v1/projects" in paths
    assert "/v1/suites" in paths
    assert "/v1/cases" in paths
    assert "/v1/agents" in paths
    assert "/v1/adapters" in paths
    assert "/v1/graders" in paths
    assert "/v1/runs" in paths
    assert "/v1/system/info" in paths


def test_dependency_overrides(settings) -> None:
    services = mock_services()
    services.get_project.execute.return_value = sample_project(name="Overridden")
    container = FakeContainer(services=services, settings=settings)
    app = create_app(container=container, settings=settings)

    app.dependency_overrides[get_actor] = lambda: Actor(id="override-actor")
    app.dependency_overrides[get_services] = lambda: services

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/v1/projects/proj-1")
        assert response.status_code == 200
        assert response.json()["name"] == "Overridden"
        query = services.get_project.execute.call_args.args[0]
        assert query.actor.id == "override-actor"

    app.dependency_overrides.clear()


def test_system_info(client, auth_headers) -> None:
    response = client.get("/v1/system/info", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "evalforge-control-plane"
    assert body["api_version"] == "v1"
    assert body["environment"] == "test"
