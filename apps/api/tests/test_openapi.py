"""OpenAPI generation tests for the Control Plane foundation."""

from __future__ import annotations


def test_openapi_generated(client) -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    spec = response.json()
    assert spec["info"]["title"]
    assert (
        "Phase 6A" in spec["info"].get("description", "")
        or "foundation" in (spec["info"].get("description") or "").lower()
    )
    paths = spec["paths"]
    assert "/health/live" in paths
    assert "/health/ready" in paths
    assert "/v1" in paths
    assert "/v1/system/info" in paths
    # Business resources are Phase 6B — must not appear yet.
    assert "/v1/projects" not in paths
    assert "/v1/runs" not in paths
    assert "/v1/suites" not in paths


def test_system_info(client, auth_headers) -> None:
    response = client.get("/v1/system/info", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "evalforge-control-plane"
    assert body["api_version"] == "v1"
    assert body["environment"] == "test"


def test_v1_root(client) -> None:
    response = client.get("/v1")
    assert response.status_code == 200
    assert response.json()["api_version"] == "v1"
    assert response.json()["status"] == "foundation"
