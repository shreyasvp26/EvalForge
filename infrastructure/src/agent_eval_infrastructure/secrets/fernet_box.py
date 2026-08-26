"""Fernet encryption helpers for user BYOK secrets at rest."""

from __future__ import annotations

import base64
import hashlib
import os
from collections.abc import Mapping

from agent_eval_domain.common.errors import InvariantViolation


def _derive_fernet_key(raw: str) -> bytes:
    """Derive a urlsafe 32-byte Fernet key from an arbitrary secret string."""
    digest = hashlib.sha256(raw.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def load_provider_secret_key(
    *,
    environ: Mapping[str, str] | None = None,
) -> bytes:
    """Resolve Fernet key material for provider credential encryption.

    Prefer ``PROVIDER_CREDENTIALS_KEY``. For local/dev only, fall back to
    ``JWT_SECRET_KEY`` so operators are not blocked. Never log the key.
    """
    env = environ if environ is not None else os.environ
    raw = (
        env.get("PROVIDER_CREDENTIALS_KEY") or env.get("JWT_SECRET_KEY") or ""
    ).strip()
    if not raw:
        raise InvariantViolation(
            "PROVIDER_CREDENTIALS_KEY (or JWT_SECRET_KEY fallback) is required "
            "to store user provider credentials",
            code="PROVIDER_CREDENTIALS_KEY_MISSING",
        )
    if len(raw) < 32:
        raise InvariantViolation(
            "PROVIDER_CREDENTIALS_KEY must be at least 32 characters",
            code="PROVIDER_CREDENTIALS_KEY_TOO_SHORT",
        )
    return _derive_fernet_key(raw)


def encrypt_secret(plaintext: str, *, key: bytes) -> str:
    try:
        from cryptography.fernet import Fernet
    except ImportError as exc:  # pragma: no cover
        raise InvariantViolation(
            "cryptography package is required for BYOK secret storage",
            code="CRYPTOGRAPHY_REQUIRED",
        ) from exc
    if not plaintext.strip():
        raise InvariantViolation(
            "credential secret must be non-empty",
            code="EMPTY_CREDENTIAL_SECRET",
        )
    token = Fernet(key).encrypt(plaintext.encode("utf-8"))
    return token.decode("ascii")


def decrypt_secret(ciphertext: str, *, key: bytes) -> str:
    try:
        from cryptography.fernet import Fernet, InvalidToken
    except ImportError as exc:  # pragma: no cover
        raise InvariantViolation(
            "cryptography package is required for BYOK secret storage",
            code="CRYPTOGRAPHY_REQUIRED",
        ) from exc
    try:
        return Fernet(key).decrypt(ciphertext.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError) as exc:
        raise InvariantViolation(
            "Failed to decrypt provider credential",
            code="PROVIDER_CREDENTIAL_DECRYPT_FAILED",
        ) from exc


def fingerprint_secret(plaintext: str) -> str:
    """Non-reversible short fingerprint for UI masking (not a secret)."""
    digest = hashlib.sha256(plaintext.encode("utf-8")).hexdigest()
    return digest[:12]
