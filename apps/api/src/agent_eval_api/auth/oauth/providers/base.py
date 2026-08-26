"""OAuth provider protocol and shared types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from agent_eval_application.ports.oauth_identity import OAuthProviderIdentity


@dataclass(frozen=True, slots=True)
class OAuthAuthorizationRequest:
    authorization_url: str


class OAuthProviderClient(Protocol):
    provider: str

    def build_authorization_url(
        self, *, state: str, nonce: str
    ) -> OAuthAuthorizationRequest: ...

    async def exchange_code(
        self, *, code: str, nonce: str
    ) -> OAuthProviderIdentity: ...
