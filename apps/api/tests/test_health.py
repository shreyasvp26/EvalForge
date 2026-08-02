"""Health and readiness endpoint tests."""

from __future__ import annotations

from agent_eval_api.main import create_app
from api_fakes import FakeContainer, mock_services
from fastapi.testclient import TestClient


def test_liveness(client) -> None:
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_ok(client) -> None:
    response = client.get("/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["checks"]["composition"] == "ok"
    assert body["checks"]["database"] == "ok"


def test_readiness_not_ready(settings) -> None:
    container = FakeContainer(services=mock_services(), settings=settings)
    container._ready = False
    app = create_app(container=container, settings=settings)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "not_ready"
    assert body["checks"]["database"] == "unavailable"


def test_health_does_not_require_auth(client) -> None:
    assert client.get("/health/live").status_code == 200
    assert client.get("/health/ready").status_code == 200
