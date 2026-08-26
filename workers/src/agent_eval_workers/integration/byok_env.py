"""Resolve BYOK secrets into sandbox environment (never logged)."""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Protocol

from agent_eval_domain.execution.provider_runtime import ProviderKey


class SecretResolver(Protocol):
    def resolve_secret_for_user(
        self, *, user_id: str, credential_ref_id: str
    ) -> tuple[object, str]: ...


_PROVIDER_ENV_VARS: dict[str, tuple[str, ...]] = {
    ProviderKey.GOOGLE.value: ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    ProviderKey.ANTHROPIC.value: ("ANTHROPIC_API_KEY",),
    ProviderKey.OPENAI.value: ("OPENAI_API_KEY",),
    ProviderKey.GROQ.value: ("GROQ_API_KEY",),
    ProviderKey.OMNIROUTE.value: ("OMNIROUTE_API_KEY",),
}


def inject_byok_into_sandbox_env(
    *,
    base_env: Mapping[str, str],
    runtime_request: Mapping[str, str],
    provider_connections: SecretResolver | None,
    allowlist: str | None = None,
) -> dict[str, str]:
    """Merge allowlisted host env with resolved user BYOK secrets.

    Secrets are injected only under known provider env var names. Values are
    never written back to runtime_request or provenance.
    """
    from agent_eval_workers.integration.sandbox_adapter import (
        sandbox_environment_from_allowlist,
    )

    env = sandbox_environment_from_allowlist(
        allowlist=allowlist,
        source=base_env if base_env is not None else os.environ,
    )
    if provider_connections is None:
        return env

    credential_ref_id = (runtime_request.get("credential_ref_id") or "").strip()
    actor_id = (runtime_request.get("requested_by_actor_id") or "").strip()
    provider_key = (runtime_request.get("provider_key") or "").strip().lower()
    if not credential_ref_id or not actor_id:
        return env
    if not credential_ref_id.startswith("user:"):
        return env

    try:
        _conn, secret = provider_connections.resolve_secret_for_user(
            user_id=actor_id,
            credential_ref_id=credential_ref_id,
        )
    except Exception:  # noqa: BLE001 — fail closed at adapter credential check
        return env

    secret = secret.strip()
    if not secret:
        return env

    env_names = _PROVIDER_ENV_VARS.get(provider_key, ())
    if not env_names and provider_key == "google":
        env_names = _PROVIDER_ENV_VARS[ProviderKey.GOOGLE.value]
    for name in env_names:
        env[name] = secret
    # Ensure allowlist includes injected keys for documentation parity.
    return env
