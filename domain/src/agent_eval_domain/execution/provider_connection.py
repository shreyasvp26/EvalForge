"""User-scoped provider connection identity (non-secret).

Secrets are stored separately via CredentialBackend.USER_SECRET_STORE.
This entity is an Application/Infrastructure concern, modeled as a frozen
value object so Domain and APIs share one redaction-safe shape.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from agent_eval_domain.common.errors import InvariantViolation
from agent_eval_domain.execution.provider_runtime import ProviderKey, parse_provider_key


class ProviderConnectionStatus(StrEnum):
    ACTIVE = "active"
    REVOKED = "revoked"


@dataclass(frozen=True, slots=True)
class ProviderConnection:
    """User-owned provider credential *identity* — never contains the secret."""

    id: str
    user_id: str
    provider_key: ProviderKey
    credential_ref_id: str
    display_name: str
    status: ProviderConnectionStatus
    created_at: datetime
    key_fingerprint: str
    """Short non-secret fingerprint for UI masking (e.g. last 4 chars hash)."""
    metadata: dict[str, str]
    """Non-secret operator/UI metadata only."""

    def __post_init__(self) -> None:
        for field_name, value in (
            ("id", self.id),
            ("user_id", self.user_id),
            ("credential_ref_id", self.credential_ref_id),
            ("display_name", self.display_name),
            ("key_fingerprint", self.key_fingerprint),
        ):
            cleaned = str(value).strip()
            if not cleaned:
                raise InvariantViolation(
                    f"provider connection {field_name} must be non-empty",
                    code="EMPTY_PROVIDER_CONNECTION_FIELD",
                    details={"field": field_name},
                )
            object.__setattr__(self, field_name, cleaned)

        if not isinstance(self.provider_key, ProviderKey):
            object.__setattr__(
                self, "provider_key", parse_provider_key(str(self.provider_key))
            )
        if not isinstance(self.status, ProviderConnectionStatus):
            object.__setattr__(
                self, "status", ProviderConnectionStatus(str(self.status))
            )

        safe_meta: dict[str, str] = {}
        for raw_key, raw_value in dict(self.metadata).items():
            key = str(raw_key).strip()
            value = str(raw_value).strip()
            if not key or not value:
                continue
            lowered = value.lower()
            if any(
                marker in lowered
                for marker in ("sk-", "api_key=", "bearer ", "password=")
            ):
                continue
            safe_meta[key] = value
        object.__setattr__(self, "metadata", safe_meta)

    @property
    def is_usable(self) -> bool:
        return self.status is ProviderConnectionStatus.ACTIVE

    def masked_key_hint(self) -> str:
        """UI-safe masked credential hint (never the secret)."""
        tip = self.key_fingerprint[-4:] if len(self.key_fingerprint) >= 4 else "****"
        return f"••••••••{tip}"

    def to_public_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "provider_key": self.provider_key.value,
            "credential_ref_id": self.credential_ref_id,
            "display_name": self.display_name,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "masked_key": self.masked_key_hint(),
            "key_fingerprint": self.key_fingerprint,
            "metadata": dict(self.metadata),
        }
