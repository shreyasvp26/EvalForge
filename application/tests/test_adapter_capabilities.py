"""Adapter capability catalog and fail-closed support matrix."""

from __future__ import annotations

from agent_eval_application.adapter_capabilities import (
    AdapterSupportStatus,
    get_adapter_capability,
    list_adapter_capabilities,
    synthetic_adapters,
    verified_live_adapters,
)
from agent_eval_application.run_identity import (
    SUPPORTED_DETERMINISTIC_ADAPTERS,
    SUPPORTED_LIVE_ADAPTERS,
)


def test_capability_catalog_matches_support_sets() -> None:
    assert verified_live_adapters() == SUPPORTED_LIVE_ADAPTERS
    assert SUPPORTED_LIVE_ADAPTERS == frozenset({"gemini_cli"})
    assert synthetic_adapters() == SUPPORTED_DETERMINISTIC_ADAPTERS
    assert SUPPORTED_DETERMINISTIC_ADAPTERS == frozenset({"claude_code"})


def test_unsupported_adapters_are_explicit() -> None:
    for key in ("cursor", "codex", "aider"):
        cap = get_adapter_capability(key)
        assert cap is not None
        assert cap.status is AdapterSupportStatus.UNSUPPORTED
        assert not cap.supports_mode("live")
        assert not cap.supports_mode("deterministic")


def test_gemini_is_verified_live() -> None:
    cap = get_adapter_capability("gemini_cli")
    assert cap is not None
    assert cap.status is AdapterSupportStatus.VERIFIED_LIVE
    assert cap.supports_mode("live")
    assert "GEMINI_API_KEY" in cap.required_credentials


def test_list_capabilities_is_sorted() -> None:
    keys = [c.adapter_key for c in list_adapter_capabilities()]
    assert keys == sorted(keys)
