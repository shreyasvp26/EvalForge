"""Worker concurrency configuration (Phase 11).

Controls how many Runs a single worker process may claim concurrently.
Safe default is 1 (sequential claim loop). Values > 1 spawn additional
claim threads, each with an isolated WorkerRuntime, so Redis claim
atomicity still prevents double-claim.
"""

from __future__ import annotations

import os


def resolve_worker_concurrency(raw: str | None = None) -> int:
    """Parse ``WORKER_CONCURRENCY``; clamp to a conservative range.

    Default: 1. Invalid values fall back to 1. Maximum allowed: 8
    (provider-safety ceiling for a single process; scale out with more
    worker processes for higher throughput).
    """
    value = (
        raw if raw is not None else os.environ.get("WORKER_CONCURRENCY", "1")
    ).strip()
    try:
        parsed = int(value)
    except ValueError:
        return 1
    if parsed < 1:
        return 1
    return min(parsed, 8)
