"""Production judge providers — plugins implementing ``JudgeProvider``.

Vendor packages live under ``anthropic``, ``openai``, and ``gemini``. Shared
retry, failure mapping, and configuration utilities live here so providers
never leak vendor exceptions into the Rubric / Grader SDK lifecycle.
"""

from __future__ import annotations

from agent_eval_graders.providers.config import ProviderConfig, require_api_key
from agent_eval_graders.providers.determinism import (
    effective_settings,
    resolve_max_tokens,
    resolve_model,
    resolve_seed,
    resolve_temperature,
)
from agent_eval_graders.providers.errors import (
    JudgeAuthenticationError,
    JudgeInvalidResponseError,
    JudgeNetworkError,
    JudgeProviderUnavailable,
    JudgeRateLimitError,
    JudgeTimeout,
    is_retryable_provider_error,
)
from agent_eval_graders.providers.retry import (
    call_with_retry,
    exponential_delay_seconds,
)
from agent_eval_graders.providers.selection import (
    create_judge_provider,
    normalize_provider_name,
)

__all__ = [
    "JudgeAuthenticationError",
    "JudgeInvalidResponseError",
    "JudgeNetworkError",
    "JudgeProviderUnavailable",
    "JudgeRateLimitError",
    "JudgeTimeout",
    "ProviderConfig",
    "call_with_retry",
    "create_judge_provider",
    "effective_settings",
    "exponential_delay_seconds",
    "is_retryable_provider_error",
    "normalize_provider_name",
    "require_api_key",
    "resolve_max_tokens",
    "resolve_model",
    "resolve_seed",
    "resolve_temperature",
]
