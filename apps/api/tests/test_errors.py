"""Error mapping: Application / shared errors → HTTP responses."""

from __future__ import annotations

from agent_eval_api.errors import error_body
from agent_eval_api.main import create_app
from agent_eval_application.errors import (
    ApplicationValidationError,
    AuthorizationError,
    ConflictError,
    DomainTranslationError,
    NotFoundApplicationError,
)
from agent_eval_domain.common.errors import InvariantViolation
from agent_eval_shared.errors import InfrastructureError
from api_fakes import FakeContainer, mock_services
from fastapi.testclient import TestClient


def _probe_client(settings, *, side_effect: BaseException) -> TestClient:
    """App with a probe route that raises ``side_effect``."""
    container = FakeContainer(services=mock_services(), settings=settings)
    app = create_app(container=container, settings=settings)

    @app.get("/__probe")
    def _probe() -> None:
        raise side_effect

    return TestClient(app, raise_server_exceptions=False)


def test_error_body_schema() -> None:
    body = error_body(code="X", message="m", details={"a": 1}, retryable=True)
    assert body == {
        "error": {
            "code": "X",
            "message": "m",
            "retryable": True,
            "details": {"a": 1},
        }
    }


def test_authorization_maps_to_403(settings) -> None:
    with _probe_client(settings, side_effect=AuthorizationError()) as client:
        response = client.get("/__probe")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"
    assert "traceback" not in response.text.lower()


def test_not_found_maps_to_404(settings) -> None:
    exc = NotFoundApplicationError(
        "missing",
        entity="Project",
        entity_id="x",
    )
    with _probe_client(settings, side_effect=exc) as client:
        response = client.get("/__probe")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_validation_maps_to_422(settings) -> None:
    exc = ApplicationValidationError("bad", code="INVALID_FIELD")
    with _probe_client(settings, side_effect=exc) as client:
        response = client.get("/__probe")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_FIELD"


def test_conflict_maps_to_409(settings) -> None:
    with _probe_client(settings, side_effect=ConflictError("dup")) as client:
        response = client.get("/__probe")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"


def test_domain_translation_invariant_maps_to_409(settings) -> None:
    domain_err = InvariantViolation("broken")
    exc = DomainTranslationError(domain_err)
    with _probe_client(settings, side_effect=exc) as client:
        response = client.get("/__probe")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVARIANT_VIOLATION"


def test_infrastructure_maps_to_503(settings) -> None:
    exc = InfrastructureError(
        "db down",
        code="DATABASE_UNAVAILABLE",
        retryable=True,
    )
    with _probe_client(settings, side_effect=exc) as client:
        response = client.get("/__probe")
    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "DATABASE_UNAVAILABLE"
    assert body["error"]["retryable"] is True


def test_unexpected_maps_to_500_without_leak(settings) -> None:
    with _probe_client(
        settings, side_effect=RuntimeError("secret internals")
    ) as client:
        response = client.get("/__probe")
    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "INTERNAL_ERROR"
    assert "secret internals" not in response.text


def test_unauthenticated_maps_to_401(client) -> None:
    response = client.get("/v1/system/info")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"
