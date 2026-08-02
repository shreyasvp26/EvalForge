"""Error mapping: Application errors → HTTP responses."""

from __future__ import annotations

from agent_eval_application.errors import (
    ApplicationValidationError,
    AuthorizationError,
    ConflictError,
    DomainTranslationError,
)
from agent_eval_domain.common.errors import InvariantViolation
from agent_eval_shared.errors import InfrastructureError
from api_fakes import NotFoundApplicationError


def test_authorization_maps_to_403(client, services, auth_headers) -> None:
    services.get_project.execute.side_effect = AuthorizationError()
    response = client.get("/v1/projects/proj-1", headers=auth_headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"
    assert "traceback" not in response.text.lower()


def test_not_found_maps_to_404(client, services, auth_headers) -> None:
    services.get_project.execute.side_effect = NotFoundApplicationError(
        "missing",
        entity="Project",
        entity_id="x",
    )
    response = client.get("/v1/projects/x", headers=auth_headers)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_validation_maps_to_422(client, services, auth_headers) -> None:
    services.create_project.execute.side_effect = ApplicationValidationError(
        "bad name",
        code="INVALID_FIELD",
    )
    response = client.post(
        "/v1/projects",
        json={"name": "Demo"},
        headers=auth_headers,
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_FIELD"


def test_conflict_maps_to_409(client, services, auth_headers) -> None:
    services.create_project.execute.side_effect = ConflictError("dup")
    response = client.post(
        "/v1/projects",
        json={"name": "Demo"},
        headers=auth_headers,
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"


def test_domain_translation_invariant_maps_to_409(
    client, services, auth_headers
) -> None:
    domain_err = InvariantViolation("broken")
    services.create_project.execute.side_effect = DomainTranslationError(domain_err)
    response = client.post(
        "/v1/projects",
        json={"name": "Demo"},
        headers=auth_headers,
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVARIANT_VIOLATION"


def test_infrastructure_maps_to_503(client, services, auth_headers) -> None:
    services.get_project.execute.side_effect = InfrastructureError(
        "db down",
        code="DATABASE_UNAVAILABLE",
        retryable=True,
    )
    response = client.get("/v1/projects/proj-1", headers=auth_headers)
    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "DATABASE_UNAVAILABLE"
    assert body["error"]["retryable"] is True


def test_unexpected_maps_to_500_without_leak(client, services, auth_headers) -> None:
    services.get_project.execute.side_effect = RuntimeError("secret internals")
    response = client.get("/v1/projects/proj-1", headers=auth_headers)
    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "INTERNAL_ERROR"
    assert "secret internals" not in response.text
