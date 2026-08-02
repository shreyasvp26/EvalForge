"""Project CRUD endpoint tests — Application services mocked."""

from __future__ import annotations

from agent_eval_application.commands.project import CreateProjectCommand
from agent_eval_application.queries.queries import GetProjectQuery
from api_fakes import NotFoundApplicationError


def test_create_project(client, services, auth_headers, container) -> None:
    response = client.post(
        "/v1/projects",
        json={"name": "Demo", "description": "d"},
        headers={**auth_headers, "Idempotency-Key": "key-1"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["id"] == "proj-1"
    assert body["name"] == "Demo"
    services.create_project.execute.assert_called_once()
    cmd = services.create_project.execute.call_args.args[0]
    assert isinstance(cmd, CreateProjectCommand)
    assert cmd.name == "Demo"
    assert cmd.idempotency_key == "key-1"
    assert cmd.actor.id == "actor-1"
    container.auth.grant.assert_called_once_with(
        actor_id="actor-1",
        project_id="proj-1",
    )


def test_get_project(client, services, auth_headers) -> None:
    response = client.get("/v1/projects/proj-1", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == "proj-1"
    query = services.get_project.execute.call_args.args[0]
    assert isinstance(query, GetProjectQuery)
    assert query.project_id == "proj-1"


def test_rename_project(client, auth_headers) -> None:
    response = client.patch(
        "/v1/projects/proj-1",
        json={"name": "Renamed"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Renamed"


def test_update_settings(client, auth_headers) -> None:
    response = client.patch(
        "/v1/projects/proj-1/settings",
        json={"settings": {"k": "v"}},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["settings"] == {"k": "v"}


def test_deprecate_project(client, auth_headers) -> None:
    response = client.post("/v1/projects/proj-1/deprecate", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "deprecated"


def test_get_project_not_found(client, services, auth_headers) -> None:
    services.get_project.execute.side_effect = NotFoundApplicationError(
        "Project not found",
        entity="Project",
        entity_id="missing",
    )
    response = client.get("/v1/projects/missing", headers=auth_headers)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_create_project_requires_auth(client) -> None:
    response = client.post("/v1/projects", json={"name": "Demo"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


def test_list_projects(client, services, auth_headers) -> None:
    response = client.get("/v1/projects", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["items"][0]["id"] == "proj-1"
    services.list_projects.execute.assert_called_once()
