"""OAuth provider identity persistence port."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

OAuthProvider = Literal["google", "github"]


@dataclass(frozen=True, slots=True)
class OAuthProviderIdentity:
    """Normalized identity from an OAuth/OIDC provider."""

    provider: OAuthProvider
    provider_user_id: str
    email: str
    email_verified: bool
    display_name: str


@dataclass(frozen=True, slots=True)
class OAuthIdentityRecord:
    """Stored link between an internal user and a provider subject."""

    id: str
    user_id: str
    provider: OAuthProvider
    provider_user_id: str
    provider_email: str | None


class OAuthIdentityPort(Protocol):
    """Resolve and persist OAuth provider identities."""

    def find_by_provider_subject(
        self,
        *,
        provider: OAuthProvider,
        provider_user_id: str,
    ) -> OAuthIdentityRecord | None:
        """Return the stored OAuth identity for a provider subject."""

    def find_by_user_and_provider(
        self,
        *,
        user_id: str,
        provider: OAuthProvider,
    ) -> OAuthIdentityRecord | None:
        """Return the OAuth identity linked to a user for a provider."""

    def resolve_oauth_login(
        self,
        identity: OAuthProviderIdentity,
    ) -> tuple[str, bool]:
        """Resolve provider identity to internal user id.

        Returns ``(user_id, created)`` where ``created`` is true when a new
        internal user row was created.
        """
