"""HTTP status / transport mapping into platform judge failures."""

from __future__ import annotations

from typing import Any

import httpx

from agent_eval_graders.providers.errors import (
    JudgeAuthenticationError,
    JudgeInvalidResponseError,
    JudgeNetworkError,
    JudgeProviderUnavailable,
    JudgeRateLimitError,
    JudgeTimeout,
)


def map_http_status(
    status_code: int,
    *,
    provider: str,
    body_preview: str = "",
    correlation_id: str | None = None,
) -> None:
    """Raise a platform failure for a non-success HTTP status. No-op for 2xx."""
    if 200 <= status_code < 300:
        return

    details: dict[str, Any] = {
        "provider": provider,
        "status_code": status_code,
    }
    if correlation_id is not None:
        details["correlation_id"] = correlation_id
    if body_preview:
        details["body_preview"] = body_preview[:200]

    if status_code in (401, 403):
        raise JudgeAuthenticationError(
            f"{provider} authentication failed (HTTP {status_code})",
            details=details,
        )
    if status_code == 429:
        raise JudgeRateLimitError(
            f"{provider} rate limited (HTTP 429)",
            details=details,
        )
    if status_code in (408, 504):
        raise JudgeTimeout(
            f"{provider} request timed out (HTTP {status_code})",
            details=details,
        )
    if 500 <= status_code < 600:
        raise JudgeProviderUnavailable(
            f"{provider} unavailable (HTTP {status_code})",
            details=details,
        )
    raise JudgeInvalidResponseError(
        f"{provider} returned unexpected HTTP {status_code}",
        details=details,
    )


def map_httpx_transport_error(
    exc: BaseException,
    *,
    provider: str,
    correlation_id: str | None = None,
) -> None:
    """Map httpx transport exceptions to platform failures (always raises)."""
    details: dict[str, Any] = {"provider": provider}
    if correlation_id is not None:
        details["correlation_id"] = correlation_id

    if isinstance(exc, httpx.TimeoutException):
        raise JudgeTimeout(
            f"{provider} request timed out",
            details=details,
            cause=exc,
        ) from exc
    if isinstance(exc, (httpx.NetworkError, httpx.RemoteProtocolError)):
        raise JudgeNetworkError(
            f"{provider} network error: {exc}",
            details=details,
            cause=exc,
        ) from exc
    if isinstance(exc, httpx.HTTPError):
        raise JudgeNetworkError(
            f"{provider} HTTP transport error: {exc}",
            details=details,
            cause=exc,
        ) from exc
    raise JudgeProviderUnavailable(
        f"{provider} request failed: {exc}",
        details=details,
        cause=exc,
    ) from exc
