"""Resolve pinned Adapter Versions into concrete Adapter SDK factories.

Never silently falls back to Claude or deterministic mode. Unsupported or
misconfigured pins fail with an actionable error.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass, field

from agent_eval_adapters.aider import AiderAdapter
from agent_eval_adapters.claude_code import ClaudeCodeAdapter
from agent_eval_adapters.codex import CodexAdapter
from agent_eval_adapters.cursor import CursorAdapter
from agent_eval_adapters.gemini import GeminiAdapter
from agent_eval_adapters.sdk.adapter import Adapter
from agent_eval_application.common.actor import Actor
from agent_eval_application.queries.queries import GetRunQuery, ListAdaptersQuery
from agent_eval_domain.common.ids import RunId
from agent_eval_shared.log import get_logger

from agent_eval_workers.integration.composition import default_claude_factory

logger = get_logger(__name__)

AdapterFactory = Callable[[], Adapter]

# Canonical keys registered for production resolution.
CLAUDE_CODE = "claude_code"
CURSOR = "cursor"
CODEX = "codex"
GEMINI_CLI = "gemini_cli"
AIDER = "aider"

_ALIASES: dict[str, str] = {
    "claude": CLAUDE_CODE,
    "claude_code": CLAUDE_CODE,
    "claude-code": CLAUDE_CODE,
    "claudecode": CLAUDE_CODE,
    "cursor": CURSOR,
    "cursor_agent": CURSOR,
    "cursor-agent": CURSOR,
    "codex": CODEX,
    "openai_codex": CODEX,
    "gemini": GEMINI_CLI,
    "gemini_cli": GEMINI_CLI,
    "gemini-cli": GEMINI_CLI,
    "aider": AIDER,
}


class AdapterResolutionError(LookupError):
    """Pinned adapter cannot be executed with the current worker configuration."""


def normalize_adapter_key(name: str) -> str | None:
    """Map Adapter.name / label tokens to a registry key, or None if unknown."""
    raw = name.strip().lower().replace(" ", "_").replace("-", "_")
    if not raw:
        return None
    if raw in _ALIASES:
        return _ALIASES[raw]
    for token, key in (
        ("claude_code", CLAUDE_CODE),
        ("claude", CLAUDE_CODE),
        ("cursor", CURSOR),
        ("codex", CODEX),
        ("gemini", GEMINI_CLI),
        ("aider", AIDER),
    ):
        if token in raw:
            return key
    return None


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
    if adapter_key == CLAUDE_CODE:
        if not os.environ.get("ANTHROPIC_API_KEY", "").strip():
            raise AdapterResolutionError(
                "Live Claude Code execution requires ANTHROPIC_API_KEY; "
                "set the credential or use WORKER_ADAPTER_MODE=deterministic "
                "for synthetic development runs"
            )
        return
    if adapter_key == CURSOR:
        # Cursor adapter uses sandbox CLI; require an explicit marker env if present.
        # Fail closed when neither Cursor- nor Anthropic-style keys exist.
        if not (
            os.environ.get("CURSOR_API_KEY", "").strip()
            or os.environ.get("ANTHROPIC_API_KEY", "").strip()
        ):
            raise AdapterResolutionError(
                "Live Cursor adapter execution requires CURSOR_API_KEY "
                "(or ANTHROPIC_API_KEY if your Cursor CLI uses it); "
                "set credentials or use WORKER_ADAPTER_MODE=deterministic"
            )
        return
    if adapter_key == CODEX:
        if not os.environ.get("OPENAI_API_KEY", "").strip():
            raise AdapterResolutionError(
                "Live Codex execution requires OPENAI_API_KEY; "
                "set the credential or use WORKER_ADAPTER_MODE=deterministic"
            )
        return
    if adapter_key == GEMINI_CLI:
        if not (
            os.environ.get("GEMINI_API_KEY", "").strip()
            or os.environ.get("GOOGLE_API_KEY", "").strip()
        ):
            raise AdapterResolutionError(
                "Live Gemini CLI execution requires GEMINI_API_KEY "
                "(or GOOGLE_API_KEY); set the credential or use "
                "WORKER_ADAPTER_MODE=deterministic"
            )
        return
    if adapter_key == AIDER:
        if not (
            os.environ.get("OPENAI_API_KEY", "").strip()
            or os.environ.get("ANTHROPIC_API_KEY", "").strip()
        ):
            raise AdapterResolutionError(
                "Live Aider execution requires OPENAI_API_KEY or ANTHROPIC_API_KEY; "
                "set a credential or use WORKER_ADAPTER_MODE=deterministic"
            )
        return
    raise AdapterResolutionError(
        f"No live credential policy configured for adapter {adapter_key!r}"
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

    def resolve(self, key: str, *, mode: str) -> AdapterFactory:
        if mode == "deterministic":
            factory = self._deterministic.get(key)
            if factory is None:
                raise AdapterResolutionError(
                    f"Adapter {key!r} has no deterministic factory registered; "
                    "deterministic mode is synthetic and only available for "
                    f"registered adapters ({', '.join(sorted(self._deterministic))})"
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
                    f"Adapter {key!r} is not registered for live execution; "
                    f"registered live adapters: {registered}"
                )
            _require_live_credentials(key)
            logger.info("adapter_mode_live", adapter_key=key)
            return factory
        raise AdapterResolutionError(f"Unknown adapter mode {mode!r}")


def default_adapter_registry() -> AdapterRegistry:
    """Register adapters that exist in the Adapter SDK package."""
    registry = AdapterRegistry()

    registry.register_live(CLAUDE_CODE, ClaudeCodeAdapter)
    registry.register_deterministic(CLAUDE_CODE, default_claude_factory())

    # Other adapters: live factories only when credentials resolve.
    # Deterministic inject exists on each SDK adapter via stream_source — register
    # deterministic only for Claude as the canonical synthetic path so we never
    # pretend Cursor/Codex ran when they did not.
    registry.register_live(CURSOR, CursorAdapter)
    registry.register_live(CODEX, CodexAdapter)
    registry.register_live(GEMINI_CLI, GeminiAdapter)
    registry.register_live(AIDER, AiderAdapter)

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
                        known = ", ".join(
                            sorted({CLAUDE_CODE, CURSOR, CODEX, GEMINI_CLI, AIDER})
                        )
                        raise AdapterResolutionError(
                            f"Pinned adapter {adapter.name!r} "
                            f"(version {version_id}) does not map to a registered "
                            f"adapter type; rename the Adapter to one of: {known}"
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
                f"version={version_id} key={key!r} mode={mode}"
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
