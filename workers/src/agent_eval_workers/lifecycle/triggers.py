"""Lifecycle triggers and failure classification."""

from __future__ import annotations

from enum import StrEnum


class LifecycleTrigger(StrEnum):
    """Deterministic events that may advance the orchestration machine."""

    CLAIM = "claim"
    BEGIN_SANDBOX_PROVISIONING = "begin_sandbox_provisioning"
    SANDBOX_READY = "sandbox_ready"
    START_ADAPTER = "start_adapter"
    ADAPTER_STARTED = "adapter_started"
    ADAPTER_FINISHED = "adapter_finished"
    PERSIST_FINAL_EVENTS = "persist_final_events"
    FINALS_PERSISTED = "finals_persisted"
    GRADING_FINISHED = "grading_finished"

    # Failure / control-plane triggers
    ADAPTER_FAILED = "adapter_failed"
    SANDBOX_FAILED = "sandbox_failed"
    REPOSITORY_FAILED = "repository_failed"
    WORKER_FAILED = "worker_failed"
    GRADING_FAILED = "grading_failed"
    TIMEOUT = "timeout"
    RESOURCE_EXHAUSTED = "resource_exhausted"
    CANCEL = "cancel"


class FailureCause(StrEnum):
    """Classified causes for a Failed terminal orchestration outcome.

    Cancellation is not a failure cause — it terminates as ``Cancelled``.
    """

    ADAPTER_FAILURE = "adapter_failure"
    ADAPTER_UNSUPPORTED = "adapter_unsupported"
    SANDBOX_FAILURE = "sandbox_failure"
    WORKER_FAILURE = "worker_failure"
    TIMEOUT = "timeout"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    REPOSITORY_PREPARATION = "repository_preparation"
    GRADING_FAILURE = "grading_failure"
