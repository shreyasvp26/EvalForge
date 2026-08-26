"""BYOK sandbox env injection tests."""

from __future__ import annotations

from types import SimpleNamespace

from agent_eval_workers.integration.byok_env import inject_byok_into_sandbox_env


class _Store:
    def resolve_secret_for_user(
        self, *, user_id: str, credential_ref_id: str
    ) -> tuple[object, str]:
        assert user_id == "user-1"
        assert credential_ref_id.startswith("user:")
        return SimpleNamespace(), "secret-gemini-key"


def test_inject_byok_maps_google_secret_to_gemini_env() -> None:
    env = inject_byok_into_sandbox_env(
        base_env={"PATH": "/usr/bin", "HOME": "/home"},
        runtime_request={
            "credential_ref_id": "user:user-1:conn:abc",
            "requested_by_actor_id": "user-1",
            "provider_key": "google",
        },
        provider_connections=_Store(),
        allowlist="PATH,HOME,GEMINI_API_KEY,GOOGLE_API_KEY",
    )
    assert env["GEMINI_API_KEY"] == "secret-gemini-key"
    assert env["GOOGLE_API_KEY"] == "secret-gemini-key"
    assert "secret-gemini-key" not in env.get("PATH", "")


def test_env_backend_refs_are_not_resolved_from_user_store() -> None:
    env = inject_byok_into_sandbox_env(
        base_env={"PATH": "/usr/bin", "GEMINI_API_KEY": "host-key"},
        runtime_request={
            "credential_ref_id": "env:GEMINI_API_KEY",
            "requested_by_actor_id": "user-1",
            "provider_key": "google",
        },
        provider_connections=_Store(),
        allowlist="PATH,GEMINI_API_KEY",
    )
    assert env["GEMINI_API_KEY"] == "host-key"
