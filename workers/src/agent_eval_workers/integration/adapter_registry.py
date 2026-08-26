"""Resolve pinned Adapter Versions into concrete Adapter SDK factories.

Authoritative support matrix (Phase 8):

- ``gemini_cli`` — live execution (canonical production coding-agent adapter)
- ``claude_code`` — deterministic/synthetic only (CI and architecture verification)

Cursor, Codex, Claude live, and Aider are **not** registered. Pins that normalize
to those keys fail closed with an actionable unsupported-adapter error. There is
never a silent fallback to Gemini or Claude.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass, field

from agent_eval_adapters.gemini import GeminiAdapter
from agent_eval_adapters.sdk.adapter import Adapter
from agent_eval_application.adapter_capabilities import get_adapter_capability
from agent_eval_application.common.actor import Actor
from agent_eval_application.queries.queries import GetRunQuery, ListAdaptersQuery
from agent_eval_application.run_identity import (
    KNOWN_ADAPTER_KEYS,
    SUPPORTED_DETERMINISTIC_ADAPTERS,
    SUPPORTED_LIVE_ADAPTERS,
    normalize_adapter_key,
)
from agent_eval_domain.common.ids import RunId
from agent_eval_shared.log import get_logger

from agent_eval_workers.integration.composition import default_claude_factory

logger = get_logger(__name__)

AdapterFactory = Callable[[], Adapter]

# Re-export canonical keys for tests / callers.
CLAUDE_CODE = "claude_code"
CURSOR = "cursor"
CODEX = "codex"
GEMINI_CLI = "gemini_cli"
AIDER = "aider"


class AdapterResolutionError(LookupError):
    """Pinned adapter cannot be executed with the current worker configuration."""

    def __init__(self, message: str, *, unsupported: bool = False) -> None:
        super().__init__(message)
        self.unsupported = unsupported


def resolve_adapter_mode(mode: str | None = None) -> str:
    """Return ``deterministic`` or ``live``.

    Default remains ``deterministic`` for CI/local architecture verification.
    Production deployments must set ``WORKER_ADAPTER_MODE=live`` explicitly.
    """
    resolved = (
        (mode or os.environ.get("WORKER_ADAPTER_MODE", "deterministic")).strip().lower()
    )
    if resolved in {"claude", "live", "cli"}:
        return "live"
    if resolved in {"deterministic", "synthetic", "test", "dev"}:
        return "deterministic"
    raise AdapterResolutionError(
        f"Unknown WORKER_ADAPTER_MODE={resolved!r}; "
        "expected 'live' (or claude/cli) or 'deterministic' (or synthetic/test/dev)"
    )


def _require_live_credentials(adapter_key: str) -> None:
    capability = get_adapter_capability(adapter_key)
    if capability is None or not capability.supports_mode("live"):
        raise AdapterResolutionError(
            f"No live credential policy configured for adapter {adapter_key!r}",
            unsupported=True,
        )
    present = any(
        os.environ.get(name, "").strip()
        for name in (*capability.required_credentials, *capability.optional_credentials)
    )
    if capability.required_credentials:
        required_ok = any(
            os.environ.get(name, "").strip() for name in capability.required_credentials
        )
        # Allow optional aliases (e.g. GOOGLE_API_KEY for Gemini) when listed.
        if not required_ok and not (
            capability.optional_credentials
            and any(
                os.environ.get(name, "").strip()
                for name in capability.optional_credentials
            )
        ):
            names = " or ".join(capability.required_credentials)
            if capability.optional_credentials:
                names = f"{names} (or {' / '.join(capability.optional_credentials)})"
            raise AdapterResolutionError(
                f"Live {capability.display_name} execution requires {names}; "
                "set the credential or use WORKER_ADAPTER_MODE=deterministic"
            )
        return
    if not present:
        names = " or ".join(
            (*capability.required_credentials, *capability.optional_credentials)
        )
        raise AdapterResolutionError(
            f"Live {capability.display_name} execution requires {names}; "
            "set a credential or use WORKER_ADAPTER_MODE=deterministic"
        )


@dataclass(slots=True)
class AdapterRegistry:
    """Maps normalized adapter keys to live / deterministic factories."""

    _live: dict[str, AdapterFactory] = field(default_factory=dict)
    _deterministic: dict[str, AdapterFactory] = field(default_factory=dict)

    def register_live(self, key: str, factory: AdapterFactory) -> None:
        self._live[key] = factory

    def register_deterministic(self, key: str, factory: AdapterFactory) -> None:
        self._deterministic[key] = factory

    def supported_live(self) -> frozenset[str]:
        return frozenset(self._live)

    def supported_deterministic(self) -> frozenset[str]:
        return frozenset(self._deterministic)

    def resolve(self, key: str, *, mode: str) -> AdapterFactory:
        if mode == "deterministic":
            factory = self._deterministic.get(key)
            if factory is None:
                registered = ", ".join(sorted(self._deterministic)) or "(none)"
                known = ", ".join(sorted(KNOWN_ADAPTER_KEYS))
                raise AdapterResolutionError(
                    f"Adapter {key!r} is not supported for deterministic execution; "
                    f"registered deterministic adapters: {registered}. "
                    f"Known adapter keys (including unsupported): {known}. "
                    "Only claude_code provides synthetic deterministic execution.",
                    unsupported=True,
                )
            logger.info(
                "adapter_mode_deterministic",
                adapter_key=key,
                detail="Synthetic development/test execution — not a live coding agent",
            )
            return factory
        if mode == "live":
            factory = self._live.get(key)
            if factory is None:
                registered = ", ".join(sorted(self._live)) or "(none)"
                raise AdapterResolutionError(
                    f"Adapter {key!r} is not supported for live execution "
                    f"(adapter_unsupported); registered live adapters: {registered}. "
                    "EvalForge marks adapters VERIFIED only after real Docker e2e. "
                    "See GET /v1/adapters/capabilities for the support matrix.",
                    unsupported=True,
                )
            _require_live_credentials(key)
            logger.info("adapter_mode_live", adapter_key=key)
            return factory
        raise AdapterResolutionError(f"Unknown adapter mode {mode!r}")


def default_adapter_registry() -> AdapterRegistry:
    """Register only adapters verified end-to-end for the requested mode."""
    registry = AdapterRegistry()

    # Deterministic/synthetic path — Claude NDJSON inject for CI verification.
    assert CLAUDE_CODE in SUPPORTED_DETERMINISTIC_ADAPTERS
    registry.register_deterministic(CLAUDE_CODE, default_claude_factory())

    # Canonical live coding-agent adapter — Gemini CLI inside Docker.
    assert GEMINI_CLI in SUPPORTED_LIVE_ADAPTERS
    registry.register_live(GEMINI_CLI, GeminiAdapter)

    return registry


@dataclass(slots=True)
class PinnedAdapterResolver:
    """Build an AdapterFactory from the Run's pinned Adapter Version."""

    actor: Actor
    get_run: object
    list_adapters: object
    registry: AdapterRegistry = field(default_factory=default_adapter_registry)
    mode: str | None = None

    def resolve_key(self, run_id: RunId) -> tuple[str, str, str]:
        """Return ``(adapter_key, adapter_name, adapter_version_id)``."""
        run = self.get_run.execute(  # type: ignore[attr-defined]
            GetRunQuery(actor=self.actor, run_id=run_id.value)
        )
        version_id = run.pins.adapter_version_id
        adapters = self.list_adapters.execute(  # type: ignore[attr-defined]
            ListAdaptersQuery(actor=self.actor)
        )
        for adapter in adapters:
            for version in adapter.versions:
                if version.id == version_id:
                    key = normalize_adapter_key(str(adapter.name))
                    if key is None:
                        key = normalize_adapter_key(str(version.label))
                    if key is None:
                        known = ", ".join(sorted(KNOWN_ADAPTER_KEYS))
                        raise AdapterResolutionError(
                            f"Pinned adapter {adapter.name!r} "
                            f"(version {version_id}) does not map to a known "
                            f"adapter type; rename the Adapter to one of: {known}",
                            unsupported=True,
                        )
                    return key, str(adapter.name), version_id
        raise AdapterResolutionError(
            f"Pinned adapter version {version_id!r} not found in adapter catalog"
        )

    def resolve_factory(self, run_id: RunId) -> AdapterFactory:
        key, name, version_id = self.resolve_key(run_id)
        mode = resolve_adapter_mode(self.mode)
        try:
            factory = self.registry.resolve(key, mode=mode)
        except AdapterResolutionError as exc:
            raise AdapterResolutionError(
                f"{exc}; requested adapter name={name!r} "
                f"version={version_id} key={key!r} mode={mode}",
                unsupported=exc.unsupported,
            ) from exc
        logger.info(
            "adapter_resolved_from_pin",
            run_id=run_id.value,
            adapter_key=key,
            adapter_name=name,
            adapter_version_id=version_id,
            mode=mode,
        )
        return factory
