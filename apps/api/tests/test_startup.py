"""Startup / shutdown lifecycle tests."""

from __future__ import annotations

from agent_eval_api.config import ApiSettings
from agent_eval_api.main import create_app
from api_fakes import FakeContainer, mock_services
from fastapi.testclient import TestClient


def test_startup_sets_container_and_shutdown_clears(settings) -> None:
    services = mock_services()
    container = FakeContainer(services=services, settings=settings)
    disposed = {"called": False}
    original_dispose = container.dispose

    def tracking_dispose() -> None:
        disposed["called"] = True
        original_dispose()

    container.dispose = tracking_dispose  # type: ignore[method-assign]

    app = create_app(container=container, settings=settings)
    with TestClient(app, raise_server_exceptions=False) as client:
        assert client.app.state.container is container
        assert client.get("/health/live").status_code == 200

    # Pre-built container is not owned by lifespan — dispose not auto-called
    assert disposed["called"] is False
    assert getattr(app.state, "container", None) is None


def test_create_app_factory_builds_without_error() -> None:
    settings = ApiSettings(environment="test", log_level="critical")
    services = mock_services()
    container = FakeContainer(services=services, settings=settings)
    app = create_app(container=container, settings=settings)
    assert app.title
    assert app.openapi_url == "/openapi.json"
