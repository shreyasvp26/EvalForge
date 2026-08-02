"""Prometheus metrics facade (System Overview §12).

Cross-cutting only — no Domain meaning. Configure once at process start
(API / Worker), then record at existing boundaries.
"""

from __future__ import annotations

from dataclasses import dataclass

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Histogram,
    generate_latest,
)

_LATENCY_BUCKETS = (
    0.005,
    0.01,
    0.025,
    0.05,
    0.1,
    0.25,
    0.5,
    1.0,
    2.5,
    5.0,
    10.0,
    30.0,
    60.0,
    120.0,
    300.0,
)


@dataclass(slots=True)
class Metrics:
    """Named collectors owned by one registry."""

    registry: CollectorRegistry
    http_requests_total: Counter
    http_request_duration_seconds: Histogram
    worker_tasks_total: Counter
    worker_task_duration_seconds: Histogram
    execution_steps_total: Counter
    execution_step_duration_seconds: Histogram
    grader_runs_total: Counter
    grader_duration_seconds: Histogram
    adapter_runs_total: Counter
    adapter_duration_seconds: Histogram
    adapter_events_total: Counter
    adapter_artifacts_total: Counter


_metrics: Metrics | None = None
_enabled: bool = False


def configure_metrics(
    *,
    enabled: bool = True,
    registry: CollectorRegistry | None = None,
    force: bool = False,
) -> Metrics | None:
    """Initialize process-wide Prometheus collectors.

    Idempotent unless ``force=True`` (tests).
    """
    global _metrics, _enabled
    if _metrics is not None and not force:
        _enabled = enabled
        return _metrics if enabled else None

    _enabled = enabled
    if not enabled:
        _metrics = None
        return None

    reg = registry or CollectorRegistry()
    _metrics = Metrics(
        registry=reg,
        http_requests_total=Counter(
            "evalforge_http_requests_total",
            "HTTP requests handled by the Control Plane",
            labelnames=("method", "endpoint", "status_code"),
            registry=reg,
        ),
        http_request_duration_seconds=Histogram(
            "evalforge_http_request_duration_seconds",
            "HTTP request duration in seconds",
            labelnames=("method", "endpoint", "status_code"),
            buckets=_LATENCY_BUCKETS,
            registry=reg,
        ),
        worker_tasks_total=Counter(
            "evalforge_worker_tasks_total",
            "Worker tasks settled by outcome",
            labelnames=("outcome",),
            registry=reg,
        ),
        worker_task_duration_seconds=Histogram(
            "evalforge_worker_task_duration_seconds",
            "Worker task hold duration in seconds",
            labelnames=("outcome",),
            buckets=_LATENCY_BUCKETS,
            registry=reg,
        ),
        execution_steps_total=Counter(
            "evalforge_execution_steps_total",
            "Execution Engine orchestration steps",
            labelnames=("trigger", "outcome"),
            registry=reg,
        ),
        execution_step_duration_seconds=Histogram(
            "evalforge_execution_step_duration_seconds",
            "Execution Engine step duration in seconds",
            labelnames=("trigger", "outcome"),
            buckets=_LATENCY_BUCKETS,
            registry=reg,
        ),
        grader_runs_total=Counter(
            "evalforge_grader_runs_total",
            "Grader SDK invocations by outcome",
            labelnames=("outcome",),
            registry=reg,
        ),
        grader_duration_seconds=Histogram(
            "evalforge_grader_duration_seconds",
            "Grader SDK invocation duration in seconds",
            labelnames=("outcome",),
            buckets=_LATENCY_BUCKETS,
            registry=reg,
        ),
        adapter_runs_total=Counter(
            "evalforge_adapter_runs_total",
            "Adapter SDK / bridge invocations by outcome",
            labelnames=("outcome",),
            registry=reg,
        ),
        adapter_duration_seconds=Histogram(
            "evalforge_adapter_duration_seconds",
            "Adapter run duration in seconds",
            labelnames=("outcome",),
            buckets=_LATENCY_BUCKETS,
            registry=reg,
        ),
        adapter_events_total=Counter(
            "evalforge_adapter_events_total",
            "Canonical events emitted by Adapters",
            registry=reg,
        ),
        adapter_artifacts_total=Counter(
            "evalforge_adapter_artifacts_total",
            "Artifacts emitted by Adapters",
            registry=reg,
        ),
    )
    return _metrics


def get_metrics() -> Metrics | None:
    """Return configured metrics when enabled; otherwise ``None``."""
    if not _enabled:
        return None
    return _metrics


def metrics_content_type() -> str:
    return CONTENT_TYPE_LATEST


def render_metrics() -> bytes:
    """Serialize the active registry for ``GET /metrics``."""
    m = get_metrics()
    if m is None:
        return b""
    return generate_latest(m.registry)


def observe_http_request(
    *,
    method: str,
    endpoint: str,
    status_code: int,
    duration_seconds: float,
) -> None:
    m = get_metrics()
    if m is None:
        return
    labels = {
        "method": method,
        "endpoint": endpoint,
        "status_code": str(status_code),
    }
    m.http_requests_total.labels(**labels).inc()
    m.http_request_duration_seconds.labels(**labels).observe(duration_seconds)


def observe_worker_task(*, outcome: str, duration_seconds: float) -> None:
    m = get_metrics()
    if m is None:
        return
    m.worker_tasks_total.labels(outcome=outcome).inc()
    m.worker_task_duration_seconds.labels(outcome=outcome).observe(duration_seconds)


def observe_execution_step(
    *,
    trigger: str,
    outcome: str,
    duration_seconds: float,
) -> None:
    m = get_metrics()
    if m is None:
        return
    m.execution_steps_total.labels(trigger=trigger, outcome=outcome).inc()
    m.execution_step_duration_seconds.labels(
        trigger=trigger,
        outcome=outcome,
    ).observe(duration_seconds)


def observe_grader_run(*, outcome: str, duration_seconds: float) -> None:
    m = get_metrics()
    if m is None:
        return
    m.grader_runs_total.labels(outcome=outcome).inc()
    m.grader_duration_seconds.labels(outcome=outcome).observe(duration_seconds)


def observe_adapter_run(
    *,
    outcome: str,
    duration_seconds: float,
    events: int = 0,
    artifacts: int = 0,
) -> None:
    m = get_metrics()
    if m is None:
        return
    m.adapter_runs_total.labels(outcome=outcome).inc()
    m.adapter_duration_seconds.labels(outcome=outcome).observe(duration_seconds)
    if events:
        m.adapter_events_total.inc(events)
    if artifacts:
        m.adapter_artifacts_total.inc(artifacts)
