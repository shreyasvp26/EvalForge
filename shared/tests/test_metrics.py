"""Shared metrics / tracing facade tests."""

from __future__ import annotations

from agent_eval_shared.metrics import (
    configure_metrics,
    get_metrics,
    observe_adapter_run,
    observe_execution_step,
    observe_grader_run,
    observe_http_request,
    observe_worker_task,
    render_metrics,
)
from agent_eval_shared.tracing import configure_tracing, get_tracer, shutdown_tracing
from prometheus_client import CollectorRegistry


def test_configure_metrics_records_and_renders() -> None:
    registry = CollectorRegistry()
    configure_metrics(enabled=True, registry=registry, force=True)
    assert get_metrics() is not None

    observe_http_request(
        method="GET",
        endpoint="/v1/projects",
        status_code=200,
        duration_seconds=0.01,
    )
    observe_worker_task(outcome="completed", duration_seconds=0.5)
    observe_execution_step(
        trigger="start_run",
        outcome="ok",
        duration_seconds=0.02,
    )
    observe_grader_run(outcome="succeeded", duration_seconds=0.1)
    observe_adapter_run(
        outcome="succeeded",
        duration_seconds=0.2,
        events=3,
        artifacts=1,
    )

    body = render_metrics().decode("utf-8")
    assert "evalforge_http_requests_total" in body
    assert "evalforge_worker_tasks_total" in body
    assert "evalforge_execution_steps_total" in body
    assert "evalforge_grader_runs_total" in body
    assert "evalforge_adapter_runs_total" in body
    assert "evalforge_adapter_events_total" in body


def test_metrics_disabled_is_noop() -> None:
    configure_metrics(enabled=False, force=True)
    assert get_metrics() is None
    observe_http_request(
        method="GET",
        endpoint="/x",
        status_code=200,
        duration_seconds=0.01,
    )
    assert render_metrics() == b""


def test_tracing_configure_disabled() -> None:
    configure_tracing(enabled=False, force=True)
    tracer = get_tracer("test")
    with tracer.start_as_current_span("noop"):
        pass
    shutdown_tracing()
