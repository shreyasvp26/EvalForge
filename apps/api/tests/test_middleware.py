"""Middleware tests — correlation, timing, logging."""

from __future__ import annotations

from agent_eval_api.middleware.timing import REQUEST_DURATION_MS_HEADER


def test_correlation_id_echoed(client) -> None:
    response = client.get(
        "/health/live",
        headers={"X-Correlation-ID": "corr-test-1"},
    )
    assert response.headers["X-Correlation-ID"] == "corr-test-1"


def test_correlation_id_generated_when_absent(client) -> None:
    response = client.get("/health/live")
    assert "X-Correlation-ID" in response.headers
    assert response.headers["X-Correlation-ID"]


def test_request_timing_header(client) -> None:
    response = client.get("/health/live")
    # Header may be lower-cased by ASGI / httpx
    duration = response.headers.get(REQUEST_DURATION_MS_HEADER) or response.headers.get(
        REQUEST_DURATION_MS_HEADER.lower()
    )
    assert duration is not None
    assert float(duration) >= 0.0


def test_auth_boundary_on_system(client, auth_headers) -> None:
    denied = client.get("/v1/system/info")
    assert denied.status_code == 401
    allowed = client.get("/v1/system/info", headers=auth_headers)
    assert allowed.status_code == 200
