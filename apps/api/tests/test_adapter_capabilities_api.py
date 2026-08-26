"""API tests for adapter capabilities and benchmark matrix."""

from __future__ import annotations


def test_adapter_capabilities_endpoint(client, auth_headers) -> None:
    response = client.get("/v1/adapters/capabilities", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["count"] >= 5
    keys = {item["adapter_key"] for item in body["items"]}
    assert "gemini_cli" in keys
    assert "cursor" in keys
    gemini = next(item for item in body["items"] if item["adapter_key"] == "gemini_cli")
    assert gemini["status"] == "verified_live"
    cursor = next(item for item in body["items"] if item["adapter_key"] == "cursor")
    assert cursor["status"] == "unsupported"


def test_benchmark_matrix_endpoint(client, services, auth_headers) -> None:
    response = client.post(
        "/v1/runs/benchmark-matrix",
        headers=auth_headers,
        json={"run_ids": ["run-1", "run-2"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["comparable"] is True
    assert body["cells"]
    assert body["cells"][0]["adapter_key"] == "gemini_cli"
    services.build_benchmark_matrix.execute.assert_called_once()
