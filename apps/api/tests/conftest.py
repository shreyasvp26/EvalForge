"""Shared fixtures for Control Plane foundation tests."""

from __future__ import annotations

import os

import pytest
from agent_eval_api.auth.jwt import issue_access_token
from agent_eval_api.config import ApiSettings
from agent_eval_api.main import create_app
from api_fakes import FakeContainer, mock_services
from fastapi.testclient import TestClient

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("LOG_LEVEL", "critical")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-for-evalforge")


@pytest.fixture
def settings() -> ApiSettings:
    return ApiSettings(
        environment="test",
        log_level="critical",
        jwt_secret_key="test-jwt-secret-key-for-evalforge",
        auth_dev_accept_bearer_as_actor_id=False,
    )


@pytest.fixture
def services():
    return mock_services()


@pytest.fixture
def container(services, settings) -> FakeContainer:
    return FakeContainer(services=services, settings=settings)


@pytest.fixture
def client(container) -> TestClient:
    app = create_app(container=container, settings=container.settings)
    # ServerErrorMiddleware re-raises after the Exception handler so ASGI
    # servers can log; disable re-raise in tests to assert HTTP bodies.
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.fixture
def auth_headers(settings: ApiSettings) -> dict[str, str]:
    token = issue_access_token("actor-1", settings)
    return {"Authorization": f"Bearer {token}"}
