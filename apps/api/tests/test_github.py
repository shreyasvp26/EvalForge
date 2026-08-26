"""GitHub connection and publication API tests."""

from __future__ import annotations

from agent_eval_application.errors import ApplicationValidationError


def test_create_github_connection_never_echoes_token(
    client, services, auth_headers
) -> None:
    response = client.post(
        "/v1/github/connections",
        headers=auth_headers,
        json={"token": "ghp_supersecret_token_value", "display_name": "Work"},
    )
    assert response.status_code == 201
    payload = response.json()
    assert "ghp_" not in str(payload)
    assert payload["masked_token"].startswith("••••")
    cmd = services.create_github_connection.execute.call_args.args[0]
    assert cmd.token == "ghp_supersecret_token_value"


def test_list_github_connections(client, services, auth_headers) -> None:
    response = client.get("/v1/github/connections", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert "ghp_" not in str(response.json())


def test_list_github_repositories(client, services, auth_headers) -> None:
    response = client.get("/v1/github/repositories", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    item = body["items"][0]
    assert item["full_name"] == "octocat/Hello-World"
    assert item["default_branch"] == "main"
    assert item["private"] is False
    assert "ghp_" not in str(body)
    cmd = services.list_github_repositories.execute.call_args.args[0]
    assert cmd.actor.id == "actor-1"


def test_list_github_branches(client, services, auth_headers) -> None:
    response = client.get(
        "/v1/github/repositories/octocat/Hello-World/branches",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert [b["name"] for b in body["items"]] == ["main", "develop"]
    cmd = services.list_github_branches.execute.call_args.args[0]
    assert cmd.owner == "octocat"
    assert cmd.repo == "Hello-World"


def test_get_github_branch_head_exact_sha(client, services, auth_headers) -> None:
    response = client.get(
        "/v1/github/repositories/octocat/Hello-World/commits/main",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["sha"] == "abcdef0123456789abcdef0123456789abcdef01"
    assert body["short_sha"] == "abcdef0"
    assert body["branch"] == "main"
    assert body["repository_url"] == "https://github.com/octocat/Hello-World"
    assert body["sha"] != "main"
    assert "ghp_" not in str(body)


def test_list_repositories_not_connected(client, services, auth_headers) -> None:
    services.list_github_repositories.execute.side_effect = ApplicationValidationError(
        "Connect GitHub in Settings to select a repository.",
        code="GITHUB_NOT_CONNECTED",
    )
    response = client.get("/v1/github/repositories", headers=auth_headers)
    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "GITHUB_NOT_CONNECTED"


def test_list_repositories_unauthorized(client, services, auth_headers) -> None:
    services.list_github_repositories.execute.side_effect = ApplicationValidationError(
        "GitHub rejected the access token or denied repository access",
        code="GITHUB_UNAUTHORIZED",
        details={"status": 401},
    )
    response = client.get("/v1/github/repositories", headers=auth_headers)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "GITHUB_UNAUTHORIZED"


def test_publish_run_returns_publication_metadata(
    client, services, auth_headers
) -> None:
    response = client.post(
        "/v1/runs/run-1/publish",
        headers=auth_headers,
        json={"base_branch": "main"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["publication"]["status"] == "published"
    assert "pull_request_url" in payload["publication"]
