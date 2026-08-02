"""Shared fixtures for Control Plane API tests."""

from __future__ import annotations

import os

import pytest
from agent_eval_api.config import ApiSettings
from agent_eval_api.main import create_app
from api_fakes import FakeContainer, mock_services
from fastapi.testclient import TestClient

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("LOG_LEVEL", "critical")


@pytest.fixture
def settings() -> ApiSettings:
    return ApiSettings(
        environment="test",
        log_level="critical",
        auth_dev_accept_bearer_as_actor_id=True,
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
    # ServerErrorMiddleware re-raises after invoking the Exception handler so
    # ASGI servers can log; disable re-raise in tests to assert HTTP bodies.
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {"Authorization": "Bearer actor-1"}
