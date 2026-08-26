"""Port for live provider API-key verification and model listing.

Infrastructure owns HTTP calls. Application never logs secrets.
Verification confirms the key works; it does not claim adapter live-capability.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol


class VerificationStatus(StrEnum):
    VALID = "valid"
    INVALID = "invalid"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class ProviderModelInfo:
    model_id: str
    display_name: str


@dataclass(frozen=True, slots=True)
class VerificationResult:
    status: VerificationStatus
    provider_key: str
    message: str
    checked_at: datetime
    models: tuple[ProviderModelInfo, ...] = ()


class ProviderVerificationPort(Protocol):
    """Minimal live probe against a provider's public API."""

    def verify_api_key(self, provider_key: str, api_key: str) -> VerificationResult:
        """Confirm the key works via a minimal authenticated call (list models)."""
        ...

    def list_available_models(
        self, provider_key: str, api_key: str
    ) -> tuple[ProviderModelInfo, ...]:
        """Return models reported by the provider for this key.

        Raises when the key is invalid or the provider cannot be reached.
        """
        ...
