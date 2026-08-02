"""API hardening — pagination helpers and transport middleware."""

from __future__ import annotations

from datetime import UTC, datetime

from agent_eval_api.config import ApiSettings
from agent_eval_api.main import create_app
from agent_eval_api.pagination import (
    encode_cursor,
    shape_collection,
)
from agent_eval_api.schemas.project import ProjectResponse
from api_fakes import FakeContainer, mock_services
from fastapi.testclient import TestClient


def _project(name: str, status: str = "active") -> ProjectResponse:
    return ProjectResponse(
        id=f"id-{name}",
        name=name,
        description=f"desc-{name}",
        status=status,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        settings={},
    )


def test_shape_collection_cursor_and_sort() -> None:
    items = [_project("b"), _project("a"), _project("c", status="deprecated")]
    page = shape_collection(items, limit=2, sort="name")
    assert [p.name for p in page.items] == ["a", "b"]
    assert page.has_more is True
    assert page.next_cursor is not None

    page2 = shape_collection(items, cursor=page.next_cursor, limit=2, sort="name")
    assert [p.name for p in page2.items] == ["c"]
    assert page2.has_more is False

    filtered = shape_collection(items, status="deprecated", limit=10)
    assert len(filtered.items) == 1
    assert filtered.items[0].name == "c"


def test_security_headers_present(client) -> None:
    response = client.get("/health/live")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"


def test_payload_too_large_rejected(settings) -> None:
    settings = ApiSettings(
        environment="test",
        log_level="critical",
        jwt_secret_key="test-jwt-secret-key-for-evalforge",
        rate_limit_enabled=False,
        max_request_body_bytes=64,
    )
    container = FakeContainer(services=mock_services(), settings=settings)
    app = create_app(container=container, settings=settings)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/v1/projects",
            content=b"x" * 200,
            headers={
                "Content-Type": "application/json",
                "Content-Length": "200",
                "Authorization": "Bearer unused",
            },
        )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"


def test_rate_limit_returns_429() -> None:
    settings = ApiSettings(
        environment="test",
        log_level="critical",
        jwt_secret_key="test-jwt-secret-key-for-evalforge",
        rate_limit_enabled=True,
        rate_limit_per_minute=2,
    )
    container = FakeContainer(services=mock_services(), settings=settings)
    app = create_app(container=container, settings=settings)
    with TestClient(app, raise_server_exceptions=False) as client:
        assert client.get("/v1/system/info").status_code in {200, 401}
        assert client.get("/v1/system/info").status_code in {200, 401}
        limited = client.get("/v1/system/info")
        assert limited.status_code == 429
        assert limited.json()["error"]["code"] == "RATE_LIMITED"


def test_list_projects_supports_limit(client, services, auth_headers) -> None:
    from api_fakes import sample_project

    services.list_projects.execute.return_value = [
        sample_project(id="p1", name="a"),
        sample_project(id="p2", name="b"),
        sample_project(id="p3", name="c"),
    ]
    response = client.get("/v1/projects?limit=1&sort=name", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["has_more"] is True
    assert body["next_cursor"]
    assert body["items"][0]["name"] == "a"


def test_encode_cursor_roundtrip() -> None:
    cursor = encode_cursor(5)
    page = shape_collection(
        [_project("a"), _project("b"), _project("c")],
        cursor=cursor,
        limit=10,
    )
    # offset 5 on 3 items → empty
    assert page.items == []
    assert page.has_more is False
