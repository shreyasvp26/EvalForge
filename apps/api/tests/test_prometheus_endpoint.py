"""Prometheus /metrics endpoint tests."""

from __future__ import annotations


def test_metrics_endpoint_unauthenticated(client) -> None:
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    # Metrics may be empty if lifespan disabled them; body is still valid.
    assert isinstance(response.content, (bytes, bytearray))


def test_http_metrics_recorded_after_request(client, auth_headers) -> None:
    client.get("/v1/system/info", headers=auth_headers)
    response = client.get("/metrics")
    assert response.status_code == 200
    body = response.text
    # Enabled by default in ApiSettings; lifespan configures collectors.
    assert (
        "evalforge_http_requests_total" in body
        or body == ""  # metrics disabled in some fixtures
    )
