"""SSE run event stream — durable DB reads with optional Redis wakeups."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

from agent_eval_api.streaming.run_events import iter_run_event_sse
from agent_eval_application.common.actor import Actor
from agent_eval_application.dto.run import (
    ExecutionEventDTO,
    RunDTO,
    RunPinsDTO,
    RunTelemetryDTO,
)


def _run(**overrides: object) -> RunDTO:
    pins = RunPinsDTO(
        project_id="proj-1",
        case_version_id="cv-1",
        prompt_version_id="pv-1",
        agent_version_id="av-1",
        adapter_version_id="adv-1",
        platform_version_id="plat-1",
        grader_version_ids=("gv-1",),
        suite_version_id=None,
    )
    base = dict(
        id="run-1",
        status="completed",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        pins=pins,
        failure_reason=None,
        failure_category=None,
        cancellation_reason=None,
        sandbox_id=None,
        expected_grader_count=1,
        produced_score_count=0,
        is_partially_graded=False,
        scores=(),
        telemetry=RunTelemetryDTO.from_cost(None),
    )
    base.update(overrides)
    return RunDTO(**base)  # type: ignore[arg-type]


def _event(sequence: int) -> ExecutionEventDTO:
    return ExecutionEventDTO(
        id=f"evt-{sequence}",
        run_id="run-1",
        sequence=sequence,
        kind="message",
        action={"kind": "message", "role": "assistant", "content_summary": "hi"},
        artifact_ids=(),
        occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
        metadata={},
    )


def test_sse_emits_backlog_and_terminal_for_completed_run() -> None:
    services = MagicMock()
    services.get_run.execute.return_value = _run(status="completed")
    services.get_run_events.execute.return_value = [_event(0), _event(1)]

    frames = list(
        iter_run_event_sse(
            services=services,
            actor=Actor(id="actor-1"),
            run_id="run-1",
            after_sequence=-1,
            redis_client=None,
        )
    )
    joined = "".join(frames)
    assert "event: run_status" in joined
    assert "event: execution_event" in joined
    assert '"sequence": 0' in joined
    assert '"sequence": 1' in joined
    assert "event: run_terminal" in joined
    assert '"status": "completed"' in joined


def test_sse_skips_events_at_or_below_cursor() -> None:
    services = MagicMock()
    services.get_run.execute.return_value = _run(status="failed", failure_reason="boom")
    services.get_run_events.execute.return_value = [_event(0), _event(1), _event(2)]

    frames = list(
        iter_run_event_sse(
            services=services,
            actor=Actor(id="actor-1"),
            run_id="run-1",
            after_sequence=1,
            redis_client=None,
        )
    )
    joined = "".join(frames)
    assert '"sequence": 2' in joined
    assert '"sequence": 0' not in joined
    assert "event: run_terminal" in joined
