"""Structured failure categories for Evaluation Runs.

Distinguishes infrastructure/execution failure from evaluation outcome
(completed run with failing scores). Categories are persisted on the Run;
free-text ``failure_reason`` remains the actionable detail.
"""

from __future__ import annotations

from enum import StrEnum


class FailureCategory(StrEnum):
    """Why a Run reached FAILED (or was cancelled as a pre-running fallback).

    Evaluation quality failures (grader ``passed=false`` on a COMPLETED run)
    are **not** represented here — those remain score/aggregate outcomes.
    """

    ADAPTER_FAILURE = "adapter_failure"
    SANDBOX_FAILURE = "sandbox_failure"
    WORKER_FAILURE = "worker_failure"
    TIMEOUT = "timeout"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    REPOSITORY_PREPARATION = "repository_preparation"
    GRADING_FAILURE = "grading_failure"
    INFRASTRUCTURE = "infrastructure"
