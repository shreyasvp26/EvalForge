"""Typed settings loading. Domain code must never import this module."""

from __future__ import annotations

from typing import Literal, cast

from pydantic import AliasChoices, Field
from pydantic import ValidationError as PydanticValidationError
from pydantic_settings import BaseSettings as PydanticBaseSettings
from pydantic_settings import SettingsConfigDict

from agent_eval_shared.errors import ConfigurationError

LogLevel = Literal["critical", "error", "warning", "info", "debug"]
Environment = Literal["development", "test", "production"]


class BaseSettings(PydanticBaseSettings):
    """Baseline settings shared by API and workers. Extend per service."""

    model_config = SettingsConfigDict(
        env_file=".env",
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
