"""End-to-end Execution Engine orchestration tests (mocked components only)."""

from __future__ import annotations

from agent_eval_domain.common.ids import RunId
from agent_eval_workers.clock import FakeClock
from agent_eval_workers.execution_engine import (
    EngineOutcomeKind,
    build_orchestration_harness,
    rebuild_worker,
)
from agent_eval_workers.lifecycle.phases import OrchestrationPhase
from agent_eval_workers.lifecycle.triggers import FailureCause
from agent_eval_workers.mocks.grader import MockGrader
from agent_eval_workers.worker import WorkerState


def test_happy_path_end_to_end() -> None:
    harness = build_orchestration_harness()
    harness.enqueue("run-1")
    result = harness.worker.run_once(block=False)
    assert result is not None
    assert result.kind is EngineOutcomeKind.COMPLETED
    assert result.phase is OrchestrationPhase.COMPLETED

    # Lifecycle driven every stage via ports
    assert harness.sandbox.provisioned == [RunId("run-1")]
    assert harness.adapter.started == [RunId("run-1")]
    assert harness.adapter.ran == [RunId("run-1")]
    assert harness.adapter.finished == [RunId("run-1")]
    assert harness.status.running == [RunId("run-1")]
    assert harness.status.grading == [RunId("run-1")]
    assert harness.status.completed == [RunId("run-1")]
    assert harness.grading.scheduled == [RunId("run-1")]
    assert len(harness.grading.scores) == 2

    # Continuous streaming — events persisted incrementally (batch_size=1)
    assert len(harness.writer.events) == 3
    assert [e.sequence for e in harness.writer.events] == [0, 1, 2]
    assert harness.writer.artifacts[0].id == "run-1-art-0"
    # Artifact before events that reference it
    assert harness.writer.artifact_write_order[0] == "run-1-art-0"
    assert harness.writer.event_write_order[-1] == "run-1-evt-2"
    assert harness.writer.events[-1].artifact_ids == ("run-1-art-0",)


def test_event_and_artifact_ordering() -> None:
    harness = build_orchestration_harness()
    harness.enqueue("run-1")
    harness.worker.run_once(block=False)
    assert harness.writer.artifact_write_order == ["run-1-art-0"]
    assert harness.writer.event_write_order == [
        "run-1-evt-0",
        "run-1-evt-1",
        "run-1-evt-2",
    ]


def test_exactly_once_persistence_on_duplicate_replay() -> None:
    from agent_eval_application.commands.run import RecordExecutionEventCommand
    from agent_eval_application.common.actor import Actor
    from agent_eval_domain.execution.ndm_codec import action_to_payload

    harness = build_orchestration_harness()
    harness.enqueue("run-1")
    harness.worker.run_once(block=False)
    assert len(harness.writer.events) == 3

    # Re-emit the same Adapter stream — Application writer is idempotent.
    harness.adapter.run(RunId("run-1"))
    assert len(harness.writer.events) == 3

    dto = harness.writer.record_execution_event(
        RecordExecutionEventCommand(
            actor=Actor(id="system-worker"),
            run_id="run-1",
            execution_event_id="run-1-evt-0",
            action=action_to_payload(harness.adapter.actions[0]),
        )
    )
    assert dto.already_recorded is True
    assert len(harness.writer.events) == 3


def test_sandbox_failure_retries_then_fails() -> None:
    harness = build_orchestration_harness(fail_sandbox=True, max_attempts=2)
    harness.enqueue("run-1")
    first = harness.worker.run_once(block=False)
    assert first is not None
    assert first.kind is EngineOutcomeKind.RECOVERABLE_FAILURE
    assert first.failure_cause is FailureCause.SANDBOX_FAILURE
    assert harness.queue.released == [RunId("run-1")]

    second = harness.worker.run_once(block=False)
    assert second is not None
    assert second.kind is EngineOutcomeKind.FAILED
    assert RunId("run-1") in harness.queue.acked
    assert harness.status.failed[-1][1] is FailureCause.SANDBOX_FAILURE


def test_adapter_failure_is_terminal() -> None:
    harness = build_orchestration_harness(fail_adapter=True, max_attempts=3)
    harness.enqueue("run-1")
    result = harness.worker.run_once(block=False)
    assert result is not None
    # Adapter failure is not retryable — finalize immediately
    assert result.kind is EngineOutcomeKind.FAILED
    assert result.failure_cause is FailureCause.ADAPTER_FAILURE
    assert harness.queue.acked == [RunId("run-1")]
    assert harness.adapter.ran == []  # failed before/during run start raise


def test_adapter_failure_during_run() -> None:
    """fail_on_run raises inside adapter.run after start."""
    harness = build_orchestration_harness(fail_adapter=True)
    harness.enqueue("run-1")
    result = harness.worker.run_once(block=False)
    assert result is not None
    assert result.kind is EngineOutcomeKind.FAILED
    assert result.failure_cause is FailureCause.ADAPTER_FAILURE
    assert harness.sandbox.destroyed  # teardown on Failed


def test_cancellation() -> None:
    harness = build_orchestration_harness()
    harness.enqueue("run-1")
    harness.cancellation.request_cancel(RunId("run-1"))
    result = harness.worker.run_once(block=False)
    assert result is not None
    assert result.kind is EngineOutcomeKind.CANCELLED
    assert harness.status.cancelled == [RunId("run-1")]
    assert harness.sandbox.destroyed
    assert harness.queue.acked == [RunId("run-1")]


def test_timeout_during_provisioning() -> None:
    clock = FakeClock()
    harness = build_orchestration_harness(
        clock=clock,
        execution_timeout_seconds=1.0,
    )

    def slow_provision(_run_id: RunId) -> None:
        clock.advance(5.0)

    harness.sandbox.after_provision = slow_provision
    harness.enqueue("run-1")
    result = harness.worker.run_once(block=False)
    assert result is not None
    assert result.kind is EngineOutcomeKind.FAILED
    assert result.failure_cause is FailureCause.TIMEOUT


def test_worker_interruption_releases_for_retry() -> None:
    harness = build_orchestration_harness()
    harness.enqueue("run-1")

    def stop_on_start(_run_id: RunId) -> None:
        harness.worker.request_stop()

    harness.adapter.after_start = stop_on_start
    result = harness.worker.run_once(block=False)
    assert result is not None
    assert result.kind is EngineOutcomeKind.INTERRUPTED
    assert harness.queue.released == [RunId("run-1")]
    assert harness.worker.state is WorkerState.STOPPED


def test_checkpoint_recovery_after_interruption() -> None:
    harness = build_orchestration_harness()
    harness.enqueue("run-1")

    def stop_on_start(_run_id: RunId) -> None:
        harness.worker.request_stop()

    harness.adapter.after_start = stop_on_start
    interrupted = harness.worker.run_once(block=False)
    assert interrupted is not None
    assert interrupted.kind is EngineOutcomeKind.INTERRUPTED

    checkpoint = harness.checkpoints.restore(RunId("run-1"))
    assert checkpoint is not None
    assert checkpoint.phase is OrchestrationPhase.ADAPTER_STARTING

    harness.adapter.after_start = None
    worker2 = rebuild_worker(harness)
    resumed = worker2.run_once(block=False)
    assert resumed is not None
    assert resumed.kind is EngineOutcomeKind.COMPLETED
    assert harness.adapter.ran == [RunId("run-1")]
    assert len(harness.writer.events) == 3


def test_recoverable_sandbox_retry_succeeds() -> None:
    harness = build_orchestration_harness(fail_sandbox=True, max_attempts=3)
    harness.enqueue("run-1")
    first = harness.worker.run_once(block=False)
    assert first is not None
    assert first.kind is EngineOutcomeKind.RECOVERABLE_FAILURE

    harness.sandbox.fail_on_provision = False
    second = harness.worker.run_once(block=False)
    assert second is not None
    assert second.kind is EngineOutcomeKind.COMPLETED
    assert len(harness.writer.events) == 3


def test_partial_grading_and_grader_failure_isolation() -> None:
    graders = (
        MockGrader(grader_id="g1", grader_version_id="gv1", numeric=0.9),
        MockGrader(grader_id="g2", grader_version_id="gv2", fail=True),
        MockGrader(grader_id="g3", grader_version_id="gv3", numeric=0.5),
    )
    harness = build_orchestration_harness(graders=graders)
    harness.enqueue("run-1")
    result = harness.worker.run_once(block=False)
    assert result is not None
    assert result.kind is EngineOutcomeKind.COMPLETED
    assert len(harness.grading.scores) == 2
    assert "g2" in harness.grading.failures
    assert [s.grader_id for s in harness.grading.scores] == ["g1", "g3"]
    # All graders still invoked (isolation — failure does not skip siblings)
    assert all(g.invocations == [RunId("run-1")] for g in graders)


def test_grading_only_after_execution() -> None:
    order: list[str] = []
    harness = build_orchestration_harness()

    def tracking_run(_run_id: RunId) -> None:
        order.append("adapter_run")

    def tracking_schedule(_run_id: RunId) -> None:
        order.append("grading")

    harness.adapter.after_run = tracking_run
    harness.grading.after_schedule = tracking_schedule
    harness.enqueue("run-1")
    harness.worker.run_once(block=False)
    assert order == ["adapter_run", "grading"]


def test_lifecycle_phases_reach_completed() -> None:
    harness = build_orchestration_harness()
    harness.enqueue("run-1")
    result = harness.worker.run_once(block=False)
    assert result is not None
    cp = harness.checkpoints.restore(RunId("run-1"))
    assert cp is not None
    assert cp.phase is OrchestrationPhase.COMPLETED
