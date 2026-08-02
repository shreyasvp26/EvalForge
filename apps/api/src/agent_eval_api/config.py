"""JWT settings and Bearer authentication for the API Layer."""

from __future__ import annotations

from agent_eval_shared.config import BaseSettings, load_settings
from pydantic import AliasChoices, Field, model_validator


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

    jwt_secret_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("JWT_SECRET_KEY", "SECRET_KEY"),
    )
    jwt_algorithm: str = Field(
        default="HS256",
        validation_alias=AliasChoices("JWT_ALGORITHM"),
    )
    jwt_issuer: str | None = Field(
        default=None,
        validation_alias=AliasChoices("JWT_ISSUER"),
    )
    jwt_audience: str | None = Field(
        default=None,
        validation_alias=AliasChoices("JWT_AUDIENCE"),
    )
    # Escape hatch for local scripts only — prefer JWT in all environments.
    auth_dev_accept_bearer_as_actor_id: bool = Field(
        default=False,
        validation_alias=AliasChoices("AUTH_DEV_ACCEPT_BEARER_AS_ACTOR_ID"),
    )
    metrics_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices("METRICS_ENABLED"),
    )
    tracing_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("TRACING_ENABLED", "OTEL_TRACES_ENABLED"),
    )
    otel_exporter_otlp_endpoint: str | None = Field(
        default=None,
        validation_alias=AliasChoices("OTEL_EXPORTER_OTLP_ENDPOINT"),
    )
    rate_limit_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices("RATE_LIMIT_ENABLED"),
    )
    rate_limit_per_minute: int = Field(
        default=120,
        ge=1,
        validation_alias=AliasChoices("RATE_LIMIT_PER_MINUTE"),
    )
    max_request_body_bytes: int = Field(
        default=1_048_576,
        ge=64,
        validation_alias=AliasChoices("MAX_REQUEST_BODY_BYTES"),
    )
    gzip_minimum_size: int = Field(
        default=500,
        ge=0,
        validation_alias=AliasChoices("GZIP_MINIMUM_SIZE"),
    )

    @model_validator(mode="after")
    def _require_jwt_or_dev_bypass(self) -> ApiSettings:
        if self.auth_dev_accept_bearer_as_actor_id:
            return self
        if not self.jwt_secret_key or not self.jwt_secret_key.strip():
            raise ValueError(
                "JWT_SECRET_KEY is required unless "
                "AUTH_DEV_ACCEPT_BEARER_AS_ACTOR_ID=true"
            )
        return self


def load_api_settings() -> ApiSettings:
    """Load and validate API settings. Raises ConfigurationError on failure."""
    return load_settings(ApiSettings)
