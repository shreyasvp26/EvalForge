"""Auth endpoint tests — login, logout, me."""

from __future__ import annotations

from agent_eval_application.errors import AuthenticationError
from api_fakes import sample_user


def test_login_returns_bearer_token(client, services) -> None:
    response = client.post(
        "/v1/auth/login",
        json={"email": "admin@evalforge.local", "password": "secret"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "Bearer"
    assert body["expires_in"] == 3600
    assert body["access_token"]
    assert body["user"]["email"] == "admin@evalforge.local"
    services.login.execute.assert_called_once()


def test_login_rejects_bad_credentials(client, services) -> None:
    services.login.execute.side_effect = AuthenticationError(
        "Invalid email or password"
    )
    response = client.post(
        "/v1/auth/login",
        json={"email": "admin@evalforge.local", "password": "wrong"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"
    assert response.headers.get("www-authenticate") == "Bearer"


def test_me_requires_auth(client) -> None:
    response = client.get("/v1/auth/me")
    assert response.status_code == 401


def test_me_returns_current_user(client, auth_headers, services) -> None:
    services.get_current_user.execute.return_value = sample_user(display_name="Ada")
    response = client.get("/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {
        "id": "user-1",
        "email": "admin@evalforge.local",
        "display_name": "Ada",
    }


def test_logout_requires_auth(client) -> None:
    response = client.post("/v1/auth/logout")
    assert response.status_code == 401


def test_logout_returns_no_content(client, auth_headers) -> None:
    response = client.post("/v1/auth/logout", headers=auth_headers)
    assert response.status_code == 204
    assert response.content == b""
