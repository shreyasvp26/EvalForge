"""Optional inference gateways (OpenAI-compatible transport, OmniRoute).

EvalForge remains authoritative over benchmarks, sandbox, grading, and provenance.
Gateways only supply model access — they never own evaluation results.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from agent_eval_domain.common.errors import InvariantViolation
from agent_eval_domain.execution.credentials import (
    CredentialReference,
    CredentialSecretResolver,
)
from agent_eval_domain.execution.provider_runtime import (
    GatewayKey,
    ModelId,
    ProviderKey,
    RoutingMode,
)

from agent_eval_application.provider_runtime import (
    DEFAULT_ENV_CREDENTIAL_REFS,
    lookup_credential_reference,
)


@dataclass(frozen=True, slots=True)
class GatewayConfig:
    """Non-secret gateway configuration (endpoint + identity)."""

    gateway_key: GatewayKey
    base_url: str
    credential_ref_id: str
    timeout_seconds: float = 60.0

    def __post_init__(self) -> None:
        url = str(self.base_url).strip().rstrip("/")
        if not url:
            raise InvariantViolation(
                "gateway base_url must be non-empty",
                code="EMPTY_GATEWAY_BASE_URL",
            )
        if "://" not in url:
            raise InvariantViolation(
                "gateway base_url must include a scheme (https://...)",
                code="INVALID_GATEWAY_BASE_URL",
            )
        object.__setattr__(self, "base_url", url)
        ref = str(self.credential_ref_id).strip()
        if not ref:
            raise InvariantViolation(
                "gateway credential_ref_id must be non-empty",
                code="EMPTY_GATEWAY_CREDENTIAL_REF",
            )
        object.__setattr__(self, "credential_ref_id", ref)


@dataclass(frozen=True, slots=True)
class InferenceRequest:
    """Minimal chat-completion style request for OpenAI-compatible gateways."""

    model: ModelId
    messages: tuple[dict[str, str], ...]
    routing_mode: RoutingMode = RoutingMode.FIXED
    temperature: float = 0.0
    max_tokens: int = 256


@dataclass(frozen=True, slots=True)
class InferenceResponse:
    """Transport response with optional actual model identity."""

    content: str
    requested_model: str
    actual_model: str | None
    provider_key: ProviderKey
    gateway_key: GatewayKey
    fallback_used: bool | None
    raw: Mapping[str, Any]


class InferenceGateway(Protocol):
    """Provider/gateway transport used for model access only."""

    @property
    def gateway_key(self) -> GatewayKey: ...

    @property
    def config(self) -> GatewayConfig: ...

    def complete(self, request: InferenceRequest) -> InferenceResponse: ...


class EnvCredentialSecretResolver:
    """Resolve ENVIRONMENT-backed credential references from process env."""

    def __init__(
        self,
        *,
        environ: Mapping[str, str] | None = None,
        catalog: Mapping[str, CredentialReference] | None = None,
    ) -> None:
        import os

        self._environ = environ if environ is not None else os.environ
        self._catalog = catalog if catalog is not None else DEFAULT_ENV_CREDENTIAL_REFS

    def resolve_secret(self, reference: CredentialReference) -> str:
        if reference.env_var_name is None:
            raise InvariantViolation(
                f"Credential reference {reference.id!r} has no env_var_name",
                code="CREDENTIAL_ENV_VAR_REQUIRED",
            )
        value = self._environ.get(reference.env_var_name, "").strip()
        if not value:
            raise InvariantViolation(
                f"Missing secret for credential reference {reference.id!r} "
                f"(env {reference.env_var_name})",
                code="CREDENTIAL_SECRET_MISSING",
                details={
                    "credential_ref_id": reference.id,
                    "env_var_name": reference.env_var_name,
                },
            )
        return value

    def resolve_by_id(self, credential_ref_id: str) -> str:
        ref = lookup_credential_reference(credential_ref_id, catalog=self._catalog)
        return self.resolve_secret(ref)


def load_omniroute_config(
    *,
    environ: Mapping[str, str] | None = None,
) -> GatewayConfig | None:
    """Parse OmniRoute gateway config from environment.

    Returns None when OmniRoute is not configured (optional).
    Never returns or embeds the API key — only credential_ref_id.
    """
    import os

    env = environ if environ is not None else os.environ
    base_url = (env.get("OMNIROUTE_BASE_URL") or "").strip()
    api_key_present = bool((env.get("OMNIROUTE_API_KEY") or "").strip())
    if not base_url and not api_key_present:
        return None
    if not base_url:
        raise InvariantViolation(
            "OMNIROUTE_API_KEY is set but OMNIROUTE_BASE_URL is missing",
            code="OMNIROUTE_BASE_URL_REQUIRED",
        )
    if not api_key_present:
        raise InvariantViolation(
            "OMNIROUTE_BASE_URL is set but OMNIROUTE_API_KEY is missing",
            code="OMNIROUTE_API_KEY_REQUIRED",
        )
    timeout_raw = (env.get("OMNIROUTE_TIMEOUT_SECONDS") or "60").strip()
    try:
        timeout = float(timeout_raw)
    except ValueError as exc:
        raise InvariantViolation(
            f"Invalid OMNIROUTE_TIMEOUT_SECONDS={timeout_raw!r}",
            code="INVALID_OMNIROUTE_TIMEOUT",
        ) from exc
    return GatewayConfig(
        gateway_key=GatewayKey.OMNIROUTE,
        base_url=base_url,
        credential_ref_id="env:OMNIROUTE_API_KEY",
        timeout_seconds=timeout,
    )


@dataclass(slots=True)
class OpenAICompatibleGateway:
    """Generic OpenAI-compatible chat completions transport.

    OmniRoute and future compatible gateways share this implementation.
    """

    config: GatewayConfig
    secrets: CredentialSecretResolver
    provider_key: ProviderKey = ProviderKey.OMNIROUTE
    http_client: Any | None = None
    """Optional injected client (tests). Must expose ``post(url, ...)`` like httpx."""

    @property
    def gateway_key(self) -> GatewayKey:
        return self.config.gateway_key

    def complete(self, request: InferenceRequest) -> InferenceResponse:
        if request.routing_mode is RoutingMode.FIXED and request.model.is_auto_token():
            raise InvariantViolation(
                "fixed routing cannot send model=auto to the gateway",
                code="FIXED_ROUTING_REJECTS_AUTO",
            )
        if (
            request.routing_mode is RoutingMode.FIXED
            and not request.model.value.strip()
        ):
            raise InvariantViolation(
                "fixed routing requires an explicit model id",
                code="FIXED_ROUTING_REQUIRES_MODEL",
            )

        if isinstance(self.secrets, EnvCredentialSecretResolver):
            api_key = self.secrets.resolve_by_id(self.config.credential_ref_id)
        else:
            api_key = self.secrets.resolve_secret(
                lookup_credential_reference(self.config.credential_ref_id)
            )

        model_param = (
            "auto" if request.routing_mode is RoutingMode.AUTO else request.model.value
        )
        url = f"{self.config.base_url}/v1/chat/completions"
        payload = {
            "model": model_param,
            "messages": list(request.messages),
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        client = self.http_client
        if client is None:
            try:
                import httpx
            except ImportError as exc:  # pragma: no cover
                raise InvariantViolation(
                    "httpx is required for OpenAI-compatible gateway transport",
                    code="HTTPX_REQUIRED",
                ) from exc
            with httpx.Client(timeout=self.config.timeout_seconds) as owned:
                response = owned.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
        else:
            response = client.post(
                url,
                json=payload,
                headers=headers,
                timeout=self.config.timeout_seconds,
            )
            if hasattr(response, "raise_for_status"):
                response.raise_for_status()
            if callable(getattr(response, "json", None)):
                data = response.json()
            else:
                data = response

        if not isinstance(data, Mapping):
            raise InvariantViolation(
                "gateway returned a non-object JSON payload",
                code="GATEWAY_INVALID_RESPONSE",
            )

        content = _extract_content(data)
        actual = _extract_actual_model(data)
        fallback = _extract_fallback(data)
        return InferenceResponse(
            content=content,
            requested_model=request.model.value,
            actual_model=actual,
            provider_key=self.provider_key,
            gateway_key=self.config.gateway_key,
            fallback_used=fallback,
            raw={k: v for k, v in data.items() if k != "error"},
        )


def create_omniroute_gateway(
    *,
    environ: Mapping[str, str] | None = None,
    http_client: Any | None = None,
    secrets: CredentialSecretResolver | None = None,
) -> OpenAICompatibleGateway | None:
    """Build an OmniRoute gateway when configured; otherwise return None."""
    config = load_omniroute_config(environ=environ)
    if config is None:
        return None
    resolver: CredentialSecretResolver = secrets or EnvCredentialSecretResolver(
        environ=environ
    )
    return OpenAICompatibleGateway(
        config=config,
        secrets=resolver,
        provider_key=ProviderKey.OMNIROUTE,
        http_client=http_client,
    )


def _extract_content(data: Mapping[str, Any]) -> str:
    choices = data.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, Mapping):
            message = first.get("message")
            if isinstance(message, Mapping):
                content = message.get("content")
                if isinstance(content, str):
                    return content
            text = first.get("text")
            if isinstance(text, str):
                return text
    content = data.get("content")
    if isinstance(content, str):
        return content
    return ""


def _extract_actual_model(data: Mapping[str, Any]) -> str | None:
    for key in ("model", "actual_model", "model_id"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _extract_fallback(data: Mapping[str, Any]) -> bool | None:
    for key in ("fallback_used", "used_fallback", "fallback"):
        if key not in data:
            continue
        value = data[key]
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes"}
    return None
