"""Typed settings loading. Domain code must never import this module."""

from __future__ import annotations

from pathlib import Path
from typing import Literal, cast

from pydantic import AliasChoices, Field
from pydantic import ValidationError as PydanticValidationError
from pydantic_settings import BaseSettings as PydanticBaseSettings
from pydantic_settings import SettingsConfigDict

from agent_eval_shared.errors import ConfigurationError

LogLevel = Literal["critical", "error", "warning", "info", "debug"]
Environment = Literal["development", "test", "production"]

_REPO_MARKERS = ("pnpm-workspace.yaml", "uv.lock", "pyproject.toml")


def find_repo_root(start: Path | None = None) -> Path | None:
    """Walk upward from ``start`` (default: CWD) looking for monorepo markers."""
    current = (start or Path.cwd()).resolve()
    for directory in (current, *current.parents):
        if any((directory / marker).exists() for marker in _REPO_MARKERS):
            # Prefer the workspace root (pnpm-workspace) when several pyprojects exist.
            if (directory / "pnpm-workspace.yaml").exists() or (
                directory / "uv.lock"
            ).exists():
                return directory
    # Fallback: nearest pyproject that also contains apps/ + infrastructure/.
    current = (start or Path.cwd()).resolve()
    for directory in (current, *current.parents):
        if (
            (directory / "pyproject.toml").exists()
            and (directory / "apps").is_dir()
            and (directory / "infrastructure").is_dir()
        ):
            return directory
    return None


def resolve_env_file() -> str | None:
    """Return the canonical ``.env`` path (repo root), independent of CWD.

    Falls back to CWD ``.env`` when the repository root cannot be detected so
    ad-hoc scripts keep working. Returns ``None`` when no file exists (pydantic
    then relies on process environment only).
    """
    candidates: list[Path] = []
    # Prefer locating the monorepo from this package's install path.
    package_root = find_repo_root(Path(__file__).resolve())
    if package_root is not None:
        candidates.append(package_root / ".env")
    cwd_root = find_repo_root(Path.cwd())
    if cwd_root is not None:
        candidates.append(cwd_root / ".env")
    candidates.append(Path.cwd() / ".env")

    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        if resolved.is_file():
            return str(resolved)
    return None


class BaseSettings(PydanticBaseSettings):
    """Baseline settings shared by API and workers. Extend per service."""

    model_config = SettingsConfigDict(
        env_file=resolve_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
    )

    environment: Environment = Field(
        default="development",
        validation_alias=AliasChoices("ENVIRONMENT", "NODE_ENV"),
    )
    log_level: LogLevel = Field(
        default="info",
        validation_alias=AliasChoices("LOG_LEVEL"),
    )


def load_settings[TSettings: BaseSettings](
    settings_cls: type[TSettings] | None = None,
) -> TSettings:
    """Load and validate settings. Raises ConfigurationError on failure."""
    cls = cast(type[TSettings], BaseSettings if settings_cls is None else settings_cls)
    try:
        return cls()
    except PydanticValidationError as exc:
        raise ConfigurationError(
            f"Invalid configuration: {exc.error_count()} validation error(s)",
            code="INVALID_CONFIGURATION",
            details={"errors": exc.errors()},
            cause=exc,
        ) from exc
