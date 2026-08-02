"""Health endpoint tests."""

from __future__ import annotations


def test_liveness(client) -> None:
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness(client) -> None:
    response = client.get("/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["checks"]["composition"] == "ok"


def test_health_does_not_require_auth(client) -> None:
    assert client.get("/health/live").status_code == 200
    assert client.get("/health/ready").status_code == 200
