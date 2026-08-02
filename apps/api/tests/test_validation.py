"""Request validation and auth boundary tests."""

from __future__ import annotations


def test_create_project_rejects_empty_name(client, auth_headers) -> None:
    response = client.post(
        "/v1/projects",
        json={"name": ""},
        headers=auth_headers,
    )
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "REQUEST_VALIDATION"
    assert "errors" in body["error"]["details"]


def test_create_project_rejects_unknown_fields(client, auth_headers) -> None:
    response = client.post(
        "/v1/projects",
        json={"name": "Demo", "extra": True},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_list_suites_requires_project_id(client, auth_headers) -> None:
    response = client.get("/v1/suites", headers=auth_headers)
    assert response.status_code == 422


def test_create_run_requires_graders(client, auth_headers) -> None:
    response = client.post(
        "/v1/runs",
        json={
            "project_id": "proj-1",
            "case_id": "case-1",
            "case_version_id": "cv-1",
            "prompt_version_id": "pv-1",
            "agent_id": "agent-1",
            "agent_version_id": "av-1",
            "adapter_version_id": "adv-1",
            "grader_version_refs": [],
            "platform_version_id": "plat-1",
        },
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_missing_bearer_rejected(client) -> None:
    response = client.get("/v1/projects/proj-1")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


def test_correlation_id_echoed(client) -> None:
    response = client.get(
        "/health/live",
        headers={"X-Correlation-ID": "corr-test-1"},
    )
    assert response.headers["X-Correlation-ID"] == "corr-test-1"
