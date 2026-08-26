"""OAuth endpoint and security behavior tests."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock
from urllib.parse import parse_qs, urlparse

import pytest
from agent_eval_api.auth.oauth.providers.google import GoogleOAuthProvider
from agent_eval_api.auth.oauth.service import OAuthService, sanitize_next_path
from agent_eval_api.auth.oauth.stores import (
    InMemoryOAuthExchangeStore,
    InMemoryOAuthStateStore,
)
from agent_eval_api.config import ApiSettings
from agent_eval_application.dto.user import UserDTO
from agent_eval_application.ports.oauth_identity import OAuthProviderIdentity
from api_fakes import FakeContainer


@pytest.fixture
def oauth_settings() -> ApiSettings:
    return ApiSettings(
        environment="test",
        log_level="critical",
        jwt_secret_key="test-jwt-secret-key-for-evalforge",
        auth_dev_accept_bearer_as_actor_id=False,
        rate_limit_enabled=False,
        oauth_google_enabled=True,
        google_client_id="google-client",
        google_client_secret="google-secret",
        google_redirect_uri="http://localhost:8000/v1/auth/google/callback",
        oauth_github_enabled=True,
        github_client_id="github-client",
        github_client_secret="github-secret",
        github_redirect_uri="http://localhost:8000/v1/auth/github/callback",
        web_app_url="http://localhost:3000",
    )


def test_sanitize_next_path_blocks_open_redirect() -> None:
    assert sanitize_next_path("//evil.example") == "/"
    assert sanitize_next_path("https://evil.example") == "/"
    assert sanitize_next_path("/projects") == "/projects"


def test_google_authorization_url_contains_state_and_scopes() -> None:
    provider = GoogleOAuthProvider(
        client_id="id",
        client_secret="secret",
        redirect_uri="http://localhost:8000/v1/auth/google/callback",
    )
    request = provider.build_authorization_url(state="state-token", nonce="nonce-token")
    assert "accounts.google.com" in request.authorization_url
    assert "state=state-token" in request.authorization_url
    assert "scope=openid+email+profile" in request.authorization_url


def test_oauth_state_cannot_be_replayed() -> None:
    state_store = InMemoryOAuthStateStore()
    token = state_store.create(provider="google", next_path="/")
    state_store.consume(token, provider="google")
    with pytest.raises(ValueError, match="Invalid or expired"):
        state_store.consume(token, provider="google")


def test_oauth_state_provider_mismatch() -> None:
    state_store = InMemoryOAuthStateStore()
    token = state_store.create(provider="google", next_path="/")
    with pytest.raises(ValueError, match="provider mismatch"):
        state_store.consume(token, provider="github")


def test_oauth_callback_issues_exchange_redirect(oauth_settings: ApiSettings) -> None:
    identity = MagicMock()
    identity.get_by_id.return_value = MagicMock(
        id="user-1", email="user@example.com", display_name="Ada"
    )
    oauth_identities = MagicMock()
    oauth_identities.resolve_oauth_login.return_value = ("user-1", True)

    google = MagicMock()
    google.build_authorization_url.side_effect = lambda *, state, nonce: MagicMock(
        authorization_url=f"https://accounts.google.com/o/oauth2/v2/auth?state={state}"
    )
    google.exchange_code = AsyncMock(
        return_value=OAuthProviderIdentity(
            provider="google",
            provider_user_id="sub-1",
            email="user@example.com",
            email_verified=True,
            display_name="Ada",
        )
    )

    state_store = InMemoryOAuthStateStore()
    exchange_store = InMemoryOAuthExchangeStore()
    service = OAuthService(
        identity=identity,
        oauth_identities=oauth_identities,
        state_store=state_store,
        exchange_store=exchange_store,
        web_app_url=oauth_settings.web_app_url,
        google=google,
        github=None,
    )

    auth_url = service.begin_authorization(provider="google", next_path="/overview")
    assert "accounts.google.com" in auth_url

    parsed = urlparse(auth_url)
    state_token = parse_qs(parsed.query)["state"][0]
    redirect = asyncio.run(
        service.complete_callback(
            provider="google",
            code="auth-code",
            state=state_token,
            error=None,
            error_description=None,
        )
    )
    assert redirect.startswith("http://localhost:3000/auth/callback?")
    assert "code=" in redirect
    assert "next=%2Foverview" in redirect


def test_oauth_providers_endpoint(
    client, container: FakeContainer, oauth_settings
) -> None:
    container.settings = oauth_settings
    response = client.get("/v1/auth/providers")
    assert response.status_code == 200
    assert response.json() == {"google": True, "github": True}


def test_oauth_exchange_returns_jwt(
    client, container: FakeContainer, oauth_settings
) -> None:
    container.settings = oauth_settings
    exchange_store = InMemoryOAuthExchangeStore()
    from agent_eval_api.auth.oauth.stores import OAuthExchangePayload

    code = exchange_store.create(
        OAuthExchangePayload(
            user_id="user-1",
            email="user@example.com",
            display_name="Ada",
        )
    )
    container.oauth.exchange_session = exchange_store.consume
    container.identity.get_by_id.return_value = MagicMock(
        id="user-1", email="user@example.com", display_name="Ada"
    )
    container.services.get_current_user.execute.return_value = UserDTO(
        id="user-1",
        email="user@example.com",
        display_name="Ada",
    )

    response = client.post("/v1/auth/oauth/exchange", json={"code": code})
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["user"]["email"] == "user@example.com"
