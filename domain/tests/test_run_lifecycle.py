from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest
from agent_eval_domain.common.errors import InvalidStateTransition, InvariantViolation
from agent_eval_domain.common.ids import (
    ArtifactId,
    ExecutionEventId,
    GraderId,
    GraderVersionId,
    SandboxId,
    ScoreId,
)
from agent_eval_domain.execution.entities import (
    ArtifactKind,
    ExecutionCost,
    ScoreValue,
)
from agent_eval_domain.execution.execution_engine import ExecutionEngine
from agent_eval_domain.execution.normalized_model import (
    FileEditAction,
    ShellCommandAction,
    ToolCallAction,
)
from agent_eval_domain.execution.run import EvaluationRun
from agent_eval_domain.execution.run_status import RunStatus
from helpers import make_direct_run_pins, make_run


def test_run_created_event_and_immutable_pins() -> None:
    run = make_run()
    events = run.pull_events()
    assert run.status is RunStatus.CREATED
    assert any(e.event_type == "RunCreated" for e in events)
    pins = run.pins
    # pins are frozen — cannot reassign fields
    with pytest.raises(FrozenInstanceError):
        pins.case_version_id = pins.case_version_id  # type: ignore[misc]


def test_happy_path_lifecycle_with_partial_grading() -> None:
    run = make_run()
    engine = ExecutionEngine()
    run.queue()
    sandbox = engine.begin_execution(
        run,
        sandbox_id=SandboxId("sbx-1"),
        adapter_version_id=run.pins.adapter_version_id,
    )
    assert run.status is RunStatus.RUNNING
    assert sandbox.id.value == "sbx-1"

    run.store_artifact(
        artifact_id=ArtifactId("art-1"),
        kind=ArtifactKind.DIFF,
        storage_key="s3://bucket/art-1",
        content_type="text/x-diff",
        size_bytes=120,
        checksum="sha256:abc",
    )
    run.record_execution_event(
        event_id=ExecutionEventId("evt-1"),
        action=ToolCallAction(tool_name="read_file", arguments={"path": "a.py"}),
    )
    run.record_execution_event(
        event_id=ExecutionEventId("evt-2"),
        action=FileEditAction(path="a.py", diff_summary="+1 -0"),
        artifact_ids=[ArtifactId("art-1")],
    )
    run.record_execution_event(
        event_id=ExecutionEventId("evt-3"),
        action=ShellCommandAction(command="pytest", exit_code=1),
    )
    assert [e.sequence for e in run.execution_events] == [0, 1, 2]

    run.record_cost(ExecutionCost(input_tokens=10, output_tokens=5, wall_clock_ms=1000))
    engine.finish_execution_successfully(run)
    assert run.status is RunStatus.GRADING

    # No scores recorded — completion is still valid (partial grading)
    run.complete()
    assert run.status is RunStatus.COMPLETED
    assert run.is_partially_graded is True


def test_score_requires_pinned_grader_and_uniqueness() -> None:
    run = make_run()
    run.queue()
    run.start(sandbox_id=SandboxId("sbx-1"))
    run.start_grading()
    grader_version_id = run.pins.grader_version_ids[0]
    run.record_score(
        score_id=ScoreId("score-1"),
        grader_id=GraderId("grader-1"),
        grader_version_id=grader_version_id,
        value=ScoreValue(passed=True),
    )
    with pytest.raises(InvariantViolation, match="at most one Score"):
        run.record_score(
            score_id=ScoreId("score-2"),
            grader_id=GraderId("grader-1"),
            grader_version_id=grader_version_id,
            value=ScoreValue(passed=False),
        )
    with pytest.raises(InvariantViolation, match="not pinned"):
        run.record_score(
            score_id=ScoreId("score-3"),
            grader_id=GraderId("other"),
            grader_version_id=GraderVersionId("gv-other"),
            value=ScoreValue(passed=True),
        )


def test_terminal_run_is_permanently_closed() -> None:
    run = make_run()
    run.queue()
    run.cancel(reason="user withdrew")
    assert run.status is RunStatus.CANCELLED
    with pytest.raises(InvariantViolation, match="permanently closed"):
        run.queue()
    with pytest.raises(InvariantViolation):
        run.record_execution_event(
            event_id=ExecutionEventId("evt-x"),
            action=ToolCallAction(tool_name="x"),
        )


def test_invalid_state_transitions() -> None:
    run = EvaluationRun.create(run_id=run_id(), pins=make_direct_run_pins())
    with pytest.raises(InvalidStateTransition):
        run.start(sandbox_id=SandboxId("sbx"))


def test_events_only_while_running() -> None:
    run = make_run()
    with pytest.raises(InvariantViolation, match="while Running"):
        run.record_execution_event(
            event_id=ExecutionEventId("evt"),
            action=ToolCallAction(tool_name="t"),
        )


def test_cost_immutable_once_written() -> None:
    run = make_run()
    run.queue()
    run.start(sandbox_id=SandboxId("sbx"))
    run.record_cost(ExecutionCost(input_tokens=1))
    with pytest.raises(InvariantViolation, match="immutable"):
        run.record_cost(ExecutionCost(input_tokens=2))


def test_execution_engine_enforces_adapter_pin() -> None:
    run = make_run()
    run.queue()
    engine = ExecutionEngine()
    from agent_eval_domain.common.ids import AdapterVersionId

    with pytest.raises(InvariantViolation, match="Adapter Version"):
        engine.begin_execution(
            run,
            sandbox_id=SandboxId("sbx"),
            adapter_version_id=AdapterVersionId("wrong"),
        )


def run_id():
    from agent_eval_domain.common.ids import RunId

    return RunId("run-direct")
