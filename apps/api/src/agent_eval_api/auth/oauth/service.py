"""OAuth orchestration — provider flows, identity resolution, session exchange."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode

from agent_eval_application.errors import AuthenticationError
from agent_eval_application.ports.identity import IdentityPort
from agent_eval_application.ports.oauth_identity import OAuthIdentityPort

from agent_eval_api.auth.oauth.providers.base import OAuthProviderClient
from agent_eval_api.auth.oauth.stores import (
    OAuthExchangePayload,
    OAuthExchangeStore,
    OAuthStateStore,
)


def sanitize_next_path(raw: str | None) -> str:
    if not raw:
        return "/"
    value = raw.strip()
    if not value.startswith("/") or value.startswith("//"):
        return "/"
    if value.startswith("/login") or value.startswith("/auth/callback"):
        return "/"
    return value


@dataclass(slots=True)
class OAuthService:
    identity: IdentityPort
    oauth_identities: OAuthIdentityPort
    state_store: OAuthStateStore
    exchange_store: OAuthExchangeStore
    web_app_url: str
    google: OAuthProviderClient | None = None
    github: OAuthProviderClient | None = None

    def provider_client(self, provider: str) -> OAuthProviderClient:
        if provider == "google":
            if self.google is None:
                raise AuthenticationError("Google sign-in is not configured")
            return self.google
        if provider == "github":
            if self.github is None:
                raise AuthenticationError("GitHub sign-in is not configured")
            return self.github
        raise AuthenticationError("Unknown OAuth provider")

    def begin_authorization(self, *, provider: str, next_path: str | None) -> str:
        client = self.provider_client(provider)
        safe_next = sanitize_next_path(next_path)
        state = self.state_store.create(provider=provider, next_path=safe_next)
        request = client.build_authorization_url(state=state, nonce=state)
        return request.authorization_url

    async def complete_callback(
        self,
        *,
        provider: str,
        code: str | None,
        state: str | None,
        error: str | None,
        error_description: str | None,
    ) -> str:
        if error:
            message = error_description or error
            raise AuthenticationError(message or "Provider sign-in was cancelled")
        if not code or not state:
            raise AuthenticationError("Missing OAuth authorization response")

        client = self.provider_client(provider)
        state_payload = self._consume_state(state, provider=provider)
        provider_identity = await client.exchange_code(
            code=code,
            nonce=state_payload.nonce,
        )
        user_id, _created = self.oauth_identities.resolve_oauth_login(provider_identity)
        identity = self.identity.get_by_id(user_id)
        if identity is None:
            raise AuthenticationError("Unable to resolve signed-in user")

        exchange_code = self.exchange_store.create(
            OAuthExchangePayload(
                user_id=identity.id,
                email=identity.email,
                display_name=identity.display_name,
            )
        )
        params = {
            "code": exchange_code,
            "next": state_payload.next_path,
        }
        return f"{self.web_app_url.rstrip('/')}/auth/callback?{urlencode(params)}"

    def exchange_session(self, code: str) -> OAuthExchangePayload:
        return self.exchange_store.consume(code)

    def _consume_state(self, token: str, *, provider: str):
        try:
            return self.state_store.consume(token, provider=provider)
        except ValueError as exc:
            raise AuthenticationError(str(exc)) from exc
