"""Exponential backoff for retryable judge-provider failures."""

from __future__ import annotations

import time
from collections.abc import Callable

from agent_eval_graders.providers.errors import is_retryable_provider_error


def exponential_delay_seconds(
    attempt: int,
    *,
    base_seconds: float = 0.5,
    max_seconds: float = 8.0,
) -> float:
    """Delay before the next attempt (``attempt`` is 0-indexed after a failure)."""
    if attempt < 0:
        return 0.0
    delay = base_seconds * (2**attempt)
    return min(delay, max_seconds)


def call_with_retry[T](
    operation: Callable[[], T],
    *,
    retry_count: int,
    base_seconds: float = 0.5,
    max_seconds: float = 8.0,
    sleep: Callable[[float], None] = time.sleep,
    is_retryable: Callable[[BaseException], bool] = is_retryable_provider_error,
) -> T:
    """Invoke ``operation``, retrying retryable failures with exponential backoff.

    ``retry_count`` is the number of retries after the first attempt
    (total attempts = retry_count + 1). Validation / auth / invalid-response
    failures are never retried.
    """
    if retry_count < 0:
        raise ValueError("retry_count must be >= 0")

    attempt = 0
    while True:
        try:
            return operation()
        except BaseException as exc:
            if not is_retryable(exc) or attempt >= retry_count:
                raise
            sleep(
                exponential_delay_seconds(
                    attempt,
                    base_seconds=base_seconds,
                    max_seconds=max_seconds,
                )
            )
            attempt += 1
