"""BYOK credential reference boundary — identity without secret material.

Secrets live in the operator environment (or a future vault). Runs, provenance,
benchmarks, logs, and API responses may only carry a CredentialReference id.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from agent_eval_domain.common.errors import InvariantViolation
from agent_eval_domain.execution.provider_runtime import ProviderKey, parse_provider_key


class CredentialBackend(StrEnum):
    """Where the secret material for a reference is resolved."""

    ENVIRONMENT = "environment"
    """Operator-managed process environment (current production path)."""

    USER_SECRET_STORE = "user_secret_store"
    """User BYOK secrets encrypted at rest (Phase 13)."""


@dataclass(frozen=True, slots=True)
class CredentialReference:
    """Opaque credential identity — never contains the secret value."""

    id: str
    provider_key: ProviderKey
    label: str
    backend: CredentialBackend = CredentialBackend.ENVIRONMENT
    """Resolution backend for the secret (not the secret itself)."""

    env_var_name: str | None = None
    """For ENVIRONMENT backend: which env var holds the secret (name only)."""

    def __post_init__(self) -> None:
        cleaned_id = str(self.id).strip()
        if not cleaned_id:
            raise InvariantViolation(
                "credential reference id must be non-empty",
                code="EMPTY_CREDENTIAL_REF_ID",
            )
        if any(
            marker in cleaned_id.lower()
            for marker in ("sk-", "api_key=", "bearer ", "password=")
        ):
            raise InvariantViolation(
                "credential reference id must not look like a secret value",
                code="CREDENTIAL_REF_LOOKS_LIKE_SECRET",
            )
        object.__setattr__(self, "id", cleaned_id)

        label = str(self.label).strip()
        if not label:
            raise InvariantViolation(
                "credential reference label must be non-empty",
                code="EMPTY_CREDENTIAL_REF_LABEL",
            )
        object.__setattr__(self, "label", label)

        if not isinstance(self.provider_key, ProviderKey):
            object.__setattr__(
                self, "provider_key", parse_provider_key(str(self.provider_key))
            )
        if not isinstance(self.backend, CredentialBackend):
            raise InvariantViolation(
                "credential backend must be a CredentialBackend",
                code="INVALID_CREDENTIAL_BACKEND",
            )

        env_name = self.env_var_name
        if env_name is not None:
            env_name = str(env_name).strip()
            if not env_name:
                env_name = None
            elif "=" in env_name or " " in env_name:
                raise InvariantViolation(
                    "env_var_name must be a bare environment variable name",
                    code="INVALID_CREDENTIAL_ENV_VAR_NAME",
                )
            object.__setattr__(self, "env_var_name", env_name)

        if self.backend is CredentialBackend.ENVIRONMENT and self.env_var_name is None:
            raise InvariantViolation(
                "environment credential references require env_var_name",
                code="CREDENTIAL_ENV_VAR_REQUIRED",
            )
        if (
            self.backend is CredentialBackend.USER_SECRET_STORE
            and self.env_var_name is not None
        ):
            raise InvariantViolation(
                "user_secret_store credential references must not set env_var_name",
                code="USER_SECRET_STORE_NO_ENV_VAR",
            )

    def to_public_dict(self) -> dict[str, str]:
        """Safe projection for API / provenance (never includes secret values)."""
        payload = {
            "credential_ref_id": self.id,
            "provider_key": self.provider_key.value,
            "label": self.label,
            "backend": self.backend.value,
        }
        if self.env_var_name is not None:
            payload["env_var_name"] = self.env_var_name
        return payload


class CredentialSecretResolver(Protocol):
    """Resolve secret material for a credential reference.

    Implementations must never log or return secrets through provenance paths.
    """

    def resolve_secret(self, reference: CredentialReference) -> str:
        """Return the raw secret for worker/gateway use only."""
        ...


def assert_no_secret_leakage(payload: object, *, context: str) -> None:
    """Defensive check used by tests and redaction helpers."""
    text = str(payload).lower()
    for marker in ("sk-", "api_key=", "bearer ", "password=", "omniroute_api_key="):
        if marker in text and "env_var_name" not in text:
            # Allow documenting env var *names* like GEMINI_API_KEY in labels.
            if marker.endswith("_key=") or marker == "api_key=":
                continue
            raise InvariantViolation(
                f"possible secret leakage in {context}",
                code="SECRET_LEAKAGE_DETECTED",
                details={"context": context},
            )
