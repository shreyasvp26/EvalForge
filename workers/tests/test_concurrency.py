"""Tests for worker concurrency configuration."""

from __future__ import annotations

from agent_eval_workers.concurrency import resolve_worker_concurrency


def test_default_concurrency_is_one() -> None:
    assert resolve_worker_concurrency("") == 1
    assert resolve_worker_concurrency("1") == 1


def test_invalid_falls_back_to_one() -> None:
    assert resolve_worker_concurrency("nope") == 1
    assert resolve_worker_concurrency("0") == 1
    assert resolve_worker_concurrency("-3") == 1


def test_clamps_to_safe_maximum() -> None:
    assert resolve_worker_concurrency("2") == 2
    assert resolve_worker_concurrency("8") == 8
    assert resolve_worker_concurrency("99") == 8
