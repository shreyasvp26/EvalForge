"""Identity / credential verification port.

Users are not Domain aggregates — identity is an Application concern that
Infrastructure stores. JWT issuance stays in the API Layer; this port only
verifies credentials and resolves user profiles for authenticated actors.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class IdentityRecord:
    """Authenticated user profile returned by the identity store."""

    id: str
    email: str
    display_name: str


class IdentityPort(Protocol):
    """Verify credentials and resolve users without exposing storage details."""

    def authenticate(self, *, email: str, password: str) -> IdentityRecord | None:
        """Return the user when credentials match; otherwise ``None``."""

    def get_by_id(self, user_id: str) -> IdentityRecord | None:
        """Resolve a user by opaque id (JWT ``sub``)."""
