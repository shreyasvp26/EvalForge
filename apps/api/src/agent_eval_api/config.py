"""API service configuration — extends shared BaseSettings."""

from __future__ import annotations

from agent_eval_shared.config import BaseSettings, load_settings
from pydantic import AliasChoices, Field


class ApiSettings(BaseSettings):
    """Control Plane process settings (transport + auth boundary only)."""

    api_host: str = Field(
        default="0.0.0.0",
        validation_alias=AliasChoices("API_HOST"),
    )
    api_port: int = Field(
        default=8000,
        validation_alias=AliasChoices("API_PORT"),
        ge=1,
        le=65535,
    )
    api_title: str = Field(default="EvalForge Control Plane")
    api_version: str = Field(default="0.1.0")
    # Development/test only: when True, accept any non-empty Bearer token as Actor id.
    # Real token issuance / verification is TODO (dedicated auth design).
    auth_dev_accept_bearer_as_actor_id: bool = Field(
        default=True,
        validation_alias=AliasChoices("AUTH_DEV_ACCEPT_BEARER_AS_ACTOR_ID"),
    )


def load_api_settings() -> ApiSettings:
    """Load and validate API settings. Raises ConfigurationError on failure."""
    return load_settings(ApiSettings)
