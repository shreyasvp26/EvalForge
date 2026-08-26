"""GitHub connection and publication API tests."""

from __future__ import annotations


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
