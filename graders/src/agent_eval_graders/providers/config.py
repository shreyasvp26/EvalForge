"""Shared judge-provider configuration primitives."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


def env_str(
    name: str,
    default: str | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> str | None:
    env = environ if environ is not None else os.environ
    value = env.get(name)
    if value is None or not value.strip():
        return default
    return value.strip()


def env_float(
    name: str,
    default: float,
    *,
    environ: Mapping[str, str] | None = None,
) -> float:
    raw = env_str(name, environ=environ)
    if raw is None:
        return default
    return float(raw)


def env_int(
    name: str,
    default: int,
    *,
    environ: Mapping[str, str] | None = None,
) -> int:
    raw = env_str(name, environ=environ)
    if raw is None:
        return default
    return int(raw)


@dataclass(frozen=True, slots=True)
class ProviderConfig:
    """Common knobs shared by all production judge providers."""

    api_key: str
    model: str
    timeout_seconds: float = 60.0
    retry_count: int = 2
    temperature: float = 0.0
    seed: int | None = 0
    max_tokens: int = 2048
    base_url: str | None = None

    def __post_init__(self) -> None:
        if not self.api_key.strip():
            raise ValueError("api_key must be non-empty")
        if not self.model.strip():
            raise ValueError("model must be non-empty")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be > 0")
        if self.retry_count < 0:
            raise ValueError("retry_count must be >= 0")
        if self.max_tokens <= 0:
            raise ValueError("max_tokens must be > 0")


def require_api_key(
    env_name: str,
    *,
    environ: Mapping[str, str] | None = None,
    explicit: str | None = None,
) -> str:
    """Resolve an API key from an explicit value or environment variable."""
    if explicit is not None and explicit.strip():
        return explicit.strip()
    value = env_str(env_name, environ=environ)
    if value is None:
        raise ValueError(f"Missing required API key: set {env_name}")
    return value


def load_common_knobs(
    *,
    environ: Mapping[str, str] | None = None,
    prefix: str,
    default_timeout: float = 60.0,
    default_retry_count: int = 2,
    default_temperature: float = 0.0,
    default_seed: int | None = 0,
    default_max_tokens: int = 2048,
) -> dict[str, Any]:
    """Load shared timeout / retry / sampling knobs from env."""
    seed_raw = env_str(f"{prefix}_SEED", environ=environ)
    seed: int | None
    if seed_raw is None:
        seed = default_seed
    elif seed_raw.lower() in {"", "none", "null"}:
        seed = None
    else:
        seed = int(seed_raw)

    return {
        "timeout_seconds": env_float(
            f"{prefix}_TIMEOUT_SECONDS",
            default_timeout,
            environ=environ,
        ),
        "retry_count": env_int(
            f"{prefix}_RETRY_COUNT",
            default_retry_count,
            environ=environ,
        ),
        "temperature": env_float(
            f"{prefix}_TEMPERATURE",
            default_temperature,
            environ=environ,
        ),
        "seed": seed,
        "max_tokens": env_int(
            f"{prefix}_MAX_TOKENS",
            default_max_tokens,
            environ=environ,
        ),
        "base_url": env_str(f"{prefix}_BASE_URL", environ=environ),
    }
