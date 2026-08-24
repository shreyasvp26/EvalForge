"""CORS middleware — explicit frontend origins for local Next.js → FastAPI."""

from __future__ import annotations

from agent_eval_api.config import ApiSettings
from agent_eval_api.main import create_app
from api_fakes import FakeContainer, mock_services
from fastapi.testclient import TestClient


def test_cors_preflight_allows_configured_origin(settings: ApiSettings) -> None:
    settings = ApiSettings(
        environment="test",
        log_level="critical",
        jwt_secret_key="test-jwt-secret-key-for-evalforge",
        rate_limit_enabled=False,
        cors_origins="http://localhost:3000",
    )
    app = create_app(
        container=FakeContainer(services=mock_services(), settings=settings),
        settings=settings,
    )
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.options(
            "/v1/projects",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": (
                    "authorization,content-type,idempotency-key"
                ),
            },
        )
    assert response.status_code in {200, 204}
    assert (
        response.headers.get("access-control-allow-origin") == "http://localhost:3000"
    )
    assert (
        "access-control-allow-credentials"
        in {k.lower() for k in response.headers.keys()}
        or response.headers.get("access-control-allow-credentials") == "true"
    )


def test_cors_get_includes_allow_origin(settings: ApiSettings) -> None:
    settings = ApiSettings(
        environment="test",
        log_level="critical",
        jwt_secret_key="test-jwt-secret-key-for-evalforge",
        rate_limit_enabled=False,
        cors_origins="http://localhost:3000,http://127.0.0.1:3000",
    )
    app = create_app(
        container=FakeContainer(services=mock_services(), settings=settings),
        settings=settings,
    )
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(
            "/health/live",
            headers={"Origin": "http://127.0.0.1:3000"},
        )
    assert response.status_code == 200
    assert (
        response.headers.get("access-control-allow-origin") == "http://127.0.0.1:3000"
    )


def test_cors_rejects_unknown_origin(settings: ApiSettings) -> None:
    settings = ApiSettings(
        environment="test",
        log_level="critical",
        jwt_secret_key="test-jwt-secret-key-for-evalforge",
        rate_limit_enabled=False,
        cors_origins="http://localhost:3000",
    )
    app = create_app(
        container=FakeContainer(services=mock_services(), settings=settings),
        settings=settings,
    )
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(
            "/health/live",
            headers={"Origin": "http://evil.example"},
        )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") != "http://evil.example"
