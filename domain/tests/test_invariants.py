"""Cross-cutting invariant tests mapped to Domain Model §8."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest
from agent_eval_domain.common.errors import InvariantViolation
from agent_eval_domain.common.ids import ArtifactId, ExecutionEventId, SandboxId
from agent_eval_domain.execution.entities import ArtifactKind
from agent_eval_domain.execution.normalized_model import ToolCallAction
from helpers import make_run


def test_invariant_4_events_append_only_ordered() -> None:
    run = make_run()
    run.queue()
    run.start(sandbox_id=SandboxId("sbx"))
    e1 = run.record_execution_event(
        event_id=ExecutionEventId("e1"),
        action=ToolCallAction(tool_name="a"),
    )
    e2 = run.record_execution_event(
        event_id=ExecutionEventId("e2"),
        action=ToolCallAction(tool_name="b"),
    )
    assert e1.sequence == 0
    assert e2.sequence == 1
    # no API to edit or delete events
    assert not hasattr(run, "update_execution_event")
    assert not hasattr(run, "delete_execution_event")


def test_invariant_5_artifacts_immutable() -> None:
    run = make_run()
    run.queue()
    run.start(sandbox_id=SandboxId("sbx"))
    artifact = run.store_artifact(
        artifact_id=ArtifactId("a1"),
        kind=ArtifactKind.LOG,
        storage_key="s3://x",
        content_type="text/plain",
        size_bytes=1,
        checksum="sha256:x",
    )
    with pytest.raises(FrozenInstanceError):
        artifact.storage_key = "s3://y"  # type: ignore[misc]


def test_invariant_6_graders_do_not_modify_runs() -> None:
    """Scores are the only grader effect on the Run aggregate."""
    run = make_run()
    run.queue()
    run.start(sandbox_id=SandboxId("sbx"))
    run.start_grading()
    status_before = run.status
    events_before = len(run.execution_events)
    # recording a score does not alter status or prior events
    from agent_eval_domain.common.ids import GraderId, ScoreId
    from agent_eval_domain.execution.entities import ScoreValue

    run.record_score(
        score_id=ScoreId("s1"),
        grader_id=GraderId("grader-1"),
        grader_version_id=run.pins.grader_version_ids[0],
        value=ScoreValue(passed=True),
    )
    assert run.status is status_before
    assert len(run.execution_events) == events_before


def test_invariant_11_sandbox_scoped_to_one_run() -> None:
    run = make_run()
    run.queue()
    sandbox = run.start(sandbox_id=SandboxId("sbx-1"))
    assert sandbox.run_id == run.id
    run.start_grading()
    assert sandbox.status.value == "destroyed"


def test_invariant_13_partial_grading_is_completed_not_new_state() -> None:
    run = make_run()
    run.queue()
    run.start(sandbox_id=SandboxId("sbx"))
    run.start_grading()
    run.complete()
    assert run.status.value == "completed"
    assert run.is_partially_graded is True


def test_cannot_record_events_after_terminal() -> None:
    run = make_run()
    run.queue()
    run.start(sandbox_id=SandboxId("sbx"))
    run.fail(reason="sandbox OOM")
    with pytest.raises(InvariantViolation):
        run.record_execution_event(
            event_id=ExecutionEventId("late"),
            action=ToolCallAction(tool_name="x"),
        )
