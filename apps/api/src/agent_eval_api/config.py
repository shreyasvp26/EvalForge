"""JWT settings and Bearer authentication for the API Layer."""

from __future__ import annotations

from agent_eval_shared.config import BaseSettings, load_settings, resolve_env_file
from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import SettingsConfigDict

# HS256 keys should be at least 32 bytes; reject well-known placeholders.
_MIN_JWT_SECRET_LENGTH = 32
_INSECURE_JWT_SECRETS = frozenset(
    {
        "change-me-in-production",
        "changeme",
        "secret",
        "jwt-secret",
        "dev",
        "test",
    }
)


class ApiSettings(BaseSettings):
    """Control Plane process settings (transport + auth boundary only)."""

    model_config = SettingsConfigDict(
        env_file=resolve_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
    )

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
    jwt_access_token_ttl_seconds: int = Field(
        default=3600,
        ge=60,
        le=86_400,
        validation_alias=AliasChoices("JWT_ACCESS_TOKEN_TTL_SECONDS"),
    )
    # Escape hatch for local scripts only — prefer JWT in all environments.
    auth_dev_accept_bearer_as_actor_id: bool = Field(
        default=False,
        validation_alias=AliasChoices("AUTH_DEV_ACCEPT_BEARER_AS_ACTOR_ID"),
    )
    auth_bootstrap_email: str | None = Field(
        default=None,
        validation_alias=AliasChoices("AUTH_BOOTSTRAP_EMAIL"),
    )
    auth_bootstrap_password: str | None = Field(
        default=None,
        validation_alias=AliasChoices("AUTH_BOOTSTRAP_PASSWORD"),
    )
    auth_bootstrap_display_name: str = Field(
        default="EvalForge Admin",
        validation_alias=AliasChoices("AUTH_BOOTSTRAP_DISPLAY_NAME"),
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
    # Comma-separated browser origins allowed to call the API (CORS).
    # Empty string disables CORS middleware (non-browser clients unaffected).
    cors_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        validation_alias=AliasChoices("CORS_ORIGINS"),
    )

    @model_validator(mode="after")
    def _require_jwt_or_dev_bypass(self) -> ApiSettings:
        if self.auth_dev_accept_bearer_as_actor_id:
            return self
        secret = (self.jwt_secret_key or "").strip()
        if not secret:
            raise ValueError(
                "JWT_SECRET_KEY is required unless "
                "AUTH_DEV_ACCEPT_BEARER_AS_ACTOR_ID=true"
            )
        if secret.lower() in _INSECURE_JWT_SECRETS:
            raise ValueError(
                "JWT_SECRET_KEY is a known insecure placeholder. Set a unique secret "
                f"of at least {_MIN_JWT_SECRET_LENGTH} characters "
                "(see .env.example)."
            )
        if len(secret) < _MIN_JWT_SECRET_LENGTH:
            raise ValueError(
                f"JWT_SECRET_KEY must be at least {_MIN_JWT_SECRET_LENGTH} characters "
                "(required for HS256; never silently use a short or placeholder secret)"
            )
        return self

    def cors_origin_list(self) -> list[str]:
        return [
            origin.strip() for origin in self.cors_origins.split(",") if origin.strip()
        ]


def load_api_settings() -> ApiSettings:
    """Load and validate API settings. Raises ConfigurationError on failure."""
    return load_settings(ApiSettings)
