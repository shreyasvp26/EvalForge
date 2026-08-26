"""Application port for user-scoped provider connections (BYOK)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from agent_eval_domain.execution.provider_connection import ProviderConnection


@dataclass(frozen=True, slots=True)
class CreateProviderConnectionInput:
    user_id: str
    provider_key: str
    api_key: str
    display_name: str = ""
    metadata: dict[str, str] = field(default_factory=dict)


class ProviderConnectionPort(Protocol):
    """CRUD + secret resolve for user BYOK connections."""

    def create(self, input: CreateProviderConnectionInput) -> ProviderConnection: ...

    def list_for_user(self, user_id: str) -> list[ProviderConnection]: ...

    def get_for_user(
        self, *, user_id: str, connection_id: str
    ) -> ProviderConnection: ...

    def revoke_for_user(
        self, *, user_id: str, connection_id: str
    ) -> ProviderConnection: ...

    def resolve_secret_for_user(
        self, *, user_id: str, credential_ref_id: str
    ) -> tuple[ProviderConnection, str]:
        """Return connection + plaintext secret for worker use only."""
        ...
