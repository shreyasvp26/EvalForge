"""Authoritative adapter capability descriptors (Phase 9).

Recognition of an adapter key is not the same as production support.
Only capabilities marked ``verified_live`` or ``synthetic_only`` may be
resolved by the worker registry for the corresponding execution mode.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal


class AdapterSupportStatus(StrEnum):
    """Production support status for an adapter capability."""

    VERIFIED_LIVE = "verified_live"
    """Live Docker e2e verified against a real coding-agent CLI."""

    SYNTHETIC_ONLY = "synthetic_only"
    """Deterministic/synthetic path for CI — not a live coding agent."""

    IMPLEMENTED_UNVERIFIED = "implemented_unverified"
    """SDK/CLI wiring exists but has not passed live Docker verification."""

    UNSUPPORTED = "unsupported"
    """Not available for production evaluation."""


ExecutionModeName = Literal["live", "deterministic"]


@dataclass(frozen=True, slots=True)
class AdapterCapability:
    """Explicit contract describing what an adapter can and cannot do."""

    adapter_key: str
    provider: str
    display_name: str
    status: AdapterSupportStatus
    execution_modes: frozenset[ExecutionModeName]
    required_credentials: tuple[str, ...]
    optional_credentials: tuple[str, ...]
    cli_package: str | None
    sandbox_install_flag: str | None
    network_required: bool
    notes: str

    def supports_mode(self, mode: ExecutionModeName) -> bool:
        return mode in self.execution_modes and self.status in {
            AdapterSupportStatus.VERIFIED_LIVE,
            AdapterSupportStatus.SYNTHETIC_ONLY,
        }


# Authoritative catalog — must stay aligned with worker AdapterRegistry.
ADAPTER_CAPABILITIES: dict[str, AdapterCapability] = {
    "gemini_cli": AdapterCapability(
        adapter_key="gemini_cli",
        provider="google",
        display_name="Gemini CLI",
        status=AdapterSupportStatus.VERIFIED_LIVE,
        execution_modes=frozenset({"live"}),
        required_credentials=("GEMINI_API_KEY",),
        optional_credentials=("GOOGLE_API_KEY",),
        cli_package="@google/gemini-cli",
        sandbox_install_flag="EVALFORGE_INSTALL_GEMINI_CLI",
        network_required=True,
        notes=(
            "Canonical live coding-agent adapter. Verified via Docker sandbox "
            "with exact repository SHA materialization and workspace grading."
        ),
    ),
    "claude_code": AdapterCapability(
        adapter_key="claude_code",
        provider="anthropic",
        display_name="Claude Code",
        status=AdapterSupportStatus.SYNTHETIC_ONLY,
        execution_modes=frozenset({"deterministic"}),
        required_credentials=(),
        optional_credentials=("ANTHROPIC_API_KEY",),
        cli_package="@anthropic-ai/claude-code",
        sandbox_install_flag="EVALFORGE_INSTALL_CLAUDE_CLI",
        network_required=False,
        notes=(
            "Synthetic NDJSON path for CI and architecture verification. "
            "Live Claude Code is NOT production-verified in EvalForge."
        ),
    ),
    "cursor": AdapterCapability(
        adapter_key="cursor",
        provider="cursor",
        display_name="Cursor Agent",
        status=AdapterSupportStatus.UNSUPPORTED,
        execution_modes=frozenset(),
        required_credentials=("CURSOR_API_KEY",),
        optional_credentials=("ANTHROPIC_API_KEY",),
        cli_package=None,
        sandbox_install_flag=None,
        network_required=True,
        notes="SDK exists; not registered for production execution.",
    ),
    "codex": AdapterCapability(
        adapter_key="codex",
        provider="openai",
        display_name="OpenAI Codex",
        status=AdapterSupportStatus.UNSUPPORTED,
        execution_modes=frozenset(),
        required_credentials=("OPENAI_API_KEY",),
        optional_credentials=(),
        cli_package=None,
        sandbox_install_flag=None,
        network_required=True,
        notes="SDK exists; not registered for production execution.",
    ),
    "aider": AdapterCapability(
        adapter_key="aider",
        provider="aider",
        display_name="Aider",
        status=AdapterSupportStatus.UNSUPPORTED,
        execution_modes=frozenset(),
        required_credentials=(),
        optional_credentials=("OPENAI_API_KEY", "ANTHROPIC_API_KEY"),
        cli_package="aider-chat",
        sandbox_install_flag=None,
        network_required=True,
        notes="SDK exists; not registered for production execution.",
    ),
}


def get_adapter_capability(adapter_key: str) -> AdapterCapability | None:
    return ADAPTER_CAPABILITIES.get(adapter_key)


def list_adapter_capabilities() -> tuple[AdapterCapability, ...]:
    return tuple(ADAPTER_CAPABILITIES[key] for key in sorted(ADAPTER_CAPABILITIES))


def verified_live_adapters() -> frozenset[str]:
    return frozenset(
        key
        for key, cap in ADAPTER_CAPABILITIES.items()
        if cap.status is AdapterSupportStatus.VERIFIED_LIVE
        and "live" in cap.execution_modes
    )


def synthetic_adapters() -> frozenset[str]:
    return frozenset(
        key
        for key, cap in ADAPTER_CAPABILITIES.items()
        if cap.status is AdapterSupportStatus.SYNTHETIC_ONLY
        and "deterministic" in cap.execution_modes
    )
