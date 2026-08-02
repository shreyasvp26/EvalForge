"""Comprehensive Worker runtime tests (mocked queue + mocked lifecycle)."""

from __future__ import annotations

from dataclasses import dataclass, field

from agent_eval_domain.common.ids import RunId
from agent_eval_workers.cancellation import InMemoryCancellationRegistry
from agent_eval_workers.checkpoints import CheckpointManager, InMemoryCheckpointStore
from agent_eval_workers.execution_engine import (
    EngineOutcomeKind,
    RecoverableExecutionError,
)
from agent_eval_workers.lifecycle.errors import IllegalLifecycleTransition
from agent_eval_workers.lifecycle.phases import OrchestrationPhase
from agent_eval_workers.lifecycle.transitions import LifecycleTransition
from agent_eval_workers.lifecycle.triggers import FailureCause, LifecycleTrigger
from agent_eval_workers.worker import (
    FakeClock,
    InMemoryWorkerQueue,
    RetryAction,
    RetryPolicy,
    WorkerRuntime,
    WorkerState,
)


@dataclass
class MockLifecycle:
    """Deterministic lifecycle stand-in (no Domain / port side effects)."""

    run_id: RunId
    phase: OrchestrationPhase = OrchestrationPhase.QUEUED
    history: list[LifecycleTransition] = field(default_factory=list)
    fail_on: LifecycleTrigger | None = None
    fail_cause: FailureCause = FailureCause.SANDBOX_FAILURE

    @property
    def is_terminal(self) -> bool:
        return self.phase in {
            OrchestrationPhase.COMPLETED,
            OrchestrationPhase.FAILED,
            OrchestrationPhase.CANCELLED,
        }

    def apply(self, trigger: LifecycleTrigger) -> LifecycleTransition:
        if self.fail_on is not None and trigger is self.fail_on:
            raise RecoverableExecutionError(
                "injected failure",
                cause=self.fail_cause,
            )

        mapping: dict[
            tuple[OrchestrationPhase, LifecycleTrigger],
            OrchestrationPhase,
        ] = {
            (
                OrchestrationPhase.QUEUED,
                LifecycleTrigger.CLAIM,
            ): OrchestrationPhase.CLAIMED,
            (
                OrchestrationPhase.CLAIMED,
                LifecycleTrigger.BEGIN_SANDBOX_PROVISIONING,
            ): OrchestrationPhase.SANDBOX_PROVISIONING,
            (
                OrchestrationPhase.SANDBOX_PROVISIONING,
                LifecycleTrigger.SANDBOX_READY,
            ): OrchestrationPhase.SANDBOX_READY,
            (
                OrchestrationPhase.SANDBOX_READY,
                LifecycleTrigger.START_ADAPTER,
            ): OrchestrationPhase.ADAPTER_STARTING,
            (
                OrchestrationPhase.ADAPTER_STARTING,
                LifecycleTrigger.ADAPTER_STARTED,
            ): OrchestrationPhase.EXECUTION_STREAMING,
            (
                OrchestrationPhase.EXECUTION_STREAMING,
                LifecycleTrigger.ADAPTER_FINISHED,
            ): OrchestrationPhase.ADAPTER_FINISHED,
            (
                OrchestrationPhase.ADAPTER_FINISHED,
                LifecycleTrigger.PERSIST_FINAL_EVENTS,
            ): OrchestrationPhase.FINAL_EVENT_PERSISTENCE,
            (
                OrchestrationPhase.FINAL_EVENT_PERSISTENCE,
                LifecycleTrigger.FINALS_PERSISTED,
            ): OrchestrationPhase.GRADING_SCHEDULED,
            (
                OrchestrationPhase.GRADING_SCHEDULED,
                LifecycleTrigger.GRADING_FINISHED,
            ): OrchestrationPhase.COMPLETED,
            (
                OrchestrationPhase.QUEUED,
                LifecycleTrigger.CANCEL,
            ): OrchestrationPhase.CANCELLED,
            (
                OrchestrationPhase.CLAIMED,
                LifecycleTrigger.CANCEL,
            ): OrchestrationPhase.CANCELLED,
            (
                OrchestrationPhase.SANDBOX_PROVISIONING,
                LifecycleTrigger.CANCEL,
            ): OrchestrationPhase.CANCELLED,
            (
                OrchestrationPhase.EXECUTION_STREAMING,
                LifecycleTrigger.CANCEL,
            ): OrchestrationPhase.CANCELLED,
            (
                OrchestrationPhase.SANDBOX_PROVISIONING,
                LifecycleTrigger.TIMEOUT,
            ): OrchestrationPhase.FAILED,
            (
                OrchestrationPhase.ADAPTER_STARTING,
                LifecycleTrigger.TIMEOUT,
            ): OrchestrationPhase.FAILED,
            (
                OrchestrationPhase.EXECUTION_STREAMING,
                LifecycleTrigger.TIMEOUT,
            ): OrchestrationPhase.FAILED,
            (
                OrchestrationPhase.SANDBOX_PROVISIONING,
                LifecycleTrigger.SANDBOX_FAILED,
            ): OrchestrationPhase.FAILED,
            (
                OrchestrationPhase.CLAIMED,
                LifecycleTrigger.WORKER_FAILED,
            ): OrchestrationPhase.FAILED,
            (
                OrchestrationPhase.SANDBOX_PROVISIONING,
                LifecycleTrigger.WORKER_FAILED,
            ): OrchestrationPhase.FAILED,
            (
                OrchestrationPhase.SANDBOX_READY,
                LifecycleTrigger.WORKER_FAILED,
            ): OrchestrationPhase.FAILED,
        }
        key = (self.phase, trigger)
        if key not in mapping:
            # Allow cancel from other non-terminal phases for tests.
            if trigger is LifecycleTrigger.CANCEL and not self.is_terminal:
                to = OrchestrationPhase.CANCELLED
            elif trigger is LifecycleTrigger.WORKER_FAILED and not self.is_terminal:
                to = OrchestrationPhase.FAILED
            else:
                raise IllegalLifecycleTransition(
                    f"illegal mock transition {self.phase} + {trigger}",
                    from_phase=self.phase.value,
                    trigger=trigger.value,
                )
        else:
            to = mapping[key]

        transition = LifecycleTransition(
            from_phase=self.phase,
            to_phase=to,
            trigger=trigger,
            failure_cause=(
                FailureCause.TIMEOUT
                if trigger is LifecycleTrigger.TIMEOUT
                else (
                    FailureCause.SANDBOX_FAILURE
                    if trigger is LifecycleTrigger.SANDBOX_FAILED
                    else (
                        FailureCause.WORKER_FAILURE
                        if trigger is LifecycleTrigger.WORKER_FAILED
                        else None
                    )
                )
            ),
        )
        self.phase = to
        self.history.append(transition)
        return transition


def _runtime(
    *,
    queue: InMemoryWorkerQueue | None = None,
    cancellation: InMemoryCancellationRegistry | None = None,
    store: InMemoryCheckpointStore | None = None,
    clock: FakeClock | None = None,
    retry: RetryPolicy | None = None,
    timeout: float | None = None,
    lifecycles: dict[str, MockLifecycle] | None = None,
) -> tuple[
    WorkerRuntime,
    InMemoryWorkerQueue,
    InMemoryCancellationRegistry,
    dict[str, MockLifecycle],
]:
    q = queue or InMemoryWorkerQueue()
    cancel = cancellation or InMemoryCancellationRegistry()
    checkpoints = CheckpointManager(store or InMemoryCheckpointStore())
    lives = lifecycles if lifecycles is not None else {}

    def factory(run_id: RunId, phase: OrchestrationPhase) -> MockLifecycle:
        key = run_id.value
        if key not in lives:
            lives[key] = MockLifecycle(run_id=run_id, phase=phase)
        else:
            lives[key].phase = phase
        return lives[key]

    worker = WorkerRuntime(
        worker_id="worker-1",
        queue=q,
        checkpoints=checkpoints,
        cancellation=cancel,
        lifecycle_factory=factory,
        retry_policy=retry or RetryPolicy(max_attempts=3),
        clock=clock or FakeClock(),
        execution_timeout_seconds=timeout,
    )
    return worker, q, cancel, lives


def test_queue_claim_and_ack_happy_path() -> None:
    worker, queue, _cancel, lives = _runtime()
    queue.enqueue(RunId("run-1"))
    result = worker.run_once(block=False)
    assert result is not None
    assert result.kind is EngineOutcomeKind.COMPLETED
    assert queue.acked == [RunId("run-1")]
    assert queue.released == []
    assert lives["run-1"].phase is OrchestrationPhase.COMPLETED
    assert queue.heartbeats  # progress heartbeats during steps


def test_retry_releases_then_succeeds() -> None:
    lives: dict[str, MockLifecycle] = {}
    worker, queue, _cancel, lives = _runtime(lifecycles=lives)
    queue.enqueue(RunId("run-1"))

    # First claim: fail once at sandbox provisioning start.
    lives["run-1"] = MockLifecycle(
        run_id=RunId("run-1"),
        fail_on=LifecycleTrigger.BEGIN_SANDBOX_PROVISIONING,
    )
    result1 = worker.run_once(block=False)
    assert result1 is not None
    assert result1.kind is EngineOutcomeKind.RECOVERABLE_FAILURE
    assert queue.released == [RunId("run-1")]
    assert queue.acked == []

    # Clear injected failure for retry claim.
    lives["run-1"].fail_on = None
    result2 = worker.run_once(block=False)
    assert result2 is not None
    assert result2.kind is EngineOutcomeKind.COMPLETED
    assert RunId("run-1") in queue.acked


def test_retries_exhausted_acks_failed() -> None:
    lives: dict[str, MockLifecycle] = {}
    worker, queue, _cancel, lives = _runtime(
        lifecycles=lives,
        retry=RetryPolicy(max_attempts=2),
    )
    queue.enqueue(RunId("run-1"))
    lives["run-1"] = MockLifecycle(
        run_id=RunId("run-1"),
        fail_on=LifecycleTrigger.BEGIN_SANDBOX_PROVISIONING,
        fail_cause=FailureCause.SANDBOX_FAILURE,
    )

    first = worker.run_once(block=False)
    assert first is not None
    assert first.kind is EngineOutcomeKind.RECOVERABLE_FAILURE
    assert queue.released == [RunId("run-1")]

    # Still failing — attempt budget exhausted → Failed + ack
    second = worker.run_once(block=False)
    assert second is not None
    assert second.kind is EngineOutcomeKind.FAILED
    assert RunId("run-1") in queue.acked


def test_cancellation_during_execution() -> None:
    worker, queue, cancel, lives = _runtime()
    queue.enqueue(RunId("run-1"))

    # Pre-create lifecycle that cancels once streaming would start.
    life = MockLifecycle(run_id=RunId("run-1"))
    lives["run-1"] = life

    original_apply = life.apply

    def apply_with_cancel(trigger: LifecycleTrigger) -> LifecycleTransition:
        if trigger is LifecycleTrigger.ADAPTER_STARTED:
            cancel.request_cancel(RunId("run-1"))
        return original_apply(trigger)

    life.apply = apply_with_cancel  # type: ignore[method-assign]

    result = worker.run_once(block=False)
    assert result is not None
    assert result.kind is EngineOutcomeKind.CANCELLED
    assert queue.acked == [RunId("run-1")]
    assert lives["run-1"].phase is OrchestrationPhase.CANCELLED


def test_execution_timeout() -> None:
    clock = FakeClock()
    worker, queue, _cancel, lives = _runtime(clock=clock, timeout=5.0)
    queue.enqueue(RunId("run-1"))
    life = MockLifecycle(run_id=RunId("run-1"))
    lives["run-1"] = life

    original_apply = life.apply

    def apply_and_advance(trigger: LifecycleTrigger) -> LifecycleTransition:
        # Blow the budget once we enter a timeout-legal phase.
        if trigger is LifecycleTrigger.BEGIN_SANDBOX_PROVISIONING:
            clock.advance(10.0)
        return original_apply(trigger)

    life.apply = apply_and_advance  # type: ignore[method-assign]

    result = worker.run_once(block=False)
    assert result is not None
    assert result.kind is EngineOutcomeKind.FAILED
    assert result.failure_cause is FailureCause.TIMEOUT
    assert queue.acked == [RunId("run-1")]


def test_checkpoint_recovery_after_crash() -> None:
    store = InMemoryCheckpointStore()
    lives: dict[str, MockLifecycle] = {}
    worker, queue, _cancel, lives = _runtime(store=store, lifecycles=lives)
    queue.enqueue(RunId("run-1"))

    life = MockLifecycle(run_id=RunId("run-1"))
    lives["run-1"] = life
    original_apply = life.apply

    def crash_on_provision(trigger: LifecycleTrigger) -> LifecycleTransition:
        if trigger is LifecycleTrigger.BEGIN_SANDBOX_PROVISIONING:
            raise RecoverableExecutionError(
                "worker crash",
                cause=FailureCause.WORKER_FAILURE,
            )
        return original_apply(trigger)

    life.apply = crash_on_provision  # type: ignore[method-assign]
    crashed = worker.run_once(block=False)
    assert crashed is not None
    assert crashed.kind is EngineOutcomeKind.RECOVERABLE_FAILURE
    assert queue.released == [RunId("run-1")]

    checkpoint = store.load(RunId("run-1"))
    assert checkpoint is not None
    assert checkpoint.phase is OrchestrationPhase.CLAIMED
    assert checkpoint.attempt == 2

    # Replacement worker resumes from checkpoint without re-CLAMing from QUEUED.
    lives["run-1"].fail_on = None
    lives["run-1"].apply = original_apply  # type: ignore[method-assign]
    lives["run-1"].history.clear()
    resumed = worker.run_once(block=False)
    assert resumed is not None
    assert resumed.kind is EngineOutcomeKind.COMPLETED
    first_trigger = lives["run-1"].history[0].trigger
    assert first_trigger is LifecycleTrigger.BEGIN_SANDBOX_PROVISIONING
    claimed_again = {t.trigger for t in lives["run-1"].history}
    assert LifecycleTrigger.CLAIM not in claimed_again


def test_worker_shutdown_releases_for_redelivery() -> None:
    worker, queue, _cancel, lives = _runtime()
    queue.enqueue(RunId("run-1"))
    life = MockLifecycle(run_id=RunId("run-1"))
    lives["run-1"] = life
    original_apply = life.apply

    def stop_midway(trigger: LifecycleTrigger) -> LifecycleTransition:
        if trigger is LifecycleTrigger.START_ADAPTER:
            worker.request_stop()
        return original_apply(trigger)

    life.apply = stop_midway  # type: ignore[method-assign]
    result = worker.run_once(block=False)
    assert result is not None
    assert result.kind is EngineOutcomeKind.INTERRUPTED
    assert queue.released == [RunId("run-1")]
    assert worker.state is WorkerState.STOPPED


def test_worker_restart_resumes_checkpoint() -> None:
    store = InMemoryCheckpointStore()
    queue = InMemoryWorkerQueue()
    cancel = InMemoryCancellationRegistry()
    lives: dict[str, MockLifecycle] = {}

    worker1, _, _, _ = _runtime(
        queue=queue,
        cancellation=cancel,
        store=store,
        lifecycles=lives,
    )
    queue.enqueue(RunId("run-1"))
    life = MockLifecycle(run_id=RunId("run-1"))
    lives["run-1"] = life
    original = life.apply

    def interrupt(trigger: LifecycleTrigger) -> LifecycleTransition:
        if trigger is LifecycleTrigger.START_ADAPTER:
            worker1.request_stop()
        return original(trigger)

    life.apply = interrupt  # type: ignore[method-assign]
    interrupted = worker1.run_once(block=False)
    assert interrupted is not None
    assert interrupted.kind is EngineOutcomeKind.INTERRUPTED

    # New worker process, same durable checkpoint store + redelivered task.
    lives2: dict[str, MockLifecycle] = {}
    worker2, _, _, lives2 = _runtime(
        queue=queue,
        cancellation=cancel,
        store=store,
        lifecycles=lives2,
    )
    restarted = worker2.run_once(block=False)
    assert restarted is not None
    assert restarted.kind is EngineOutcomeKind.COMPLETED
    assert store.load(RunId("run-1")) is not None
    assert lives2["run-1"].phase is OrchestrationPhase.COMPLETED


def test_already_terminal_redelivery_acks() -> None:
    store = InMemoryCheckpointStore()
    manager = CheckpointManager(store)
    manager.create(RunId("run-1"), OrchestrationPhase.COMPLETED, attempt=1)
    worker, queue, _cancel, _lives = _runtime(store=store)
    queue.enqueue(RunId("run-1"))
    result = worker.run_once(block=False)
    assert result is not None
    assert result.kind is EngineOutcomeKind.ALREADY_TERMINAL
    assert queue.acked == [RunId("run-1")]


def test_retry_policy_classification() -> None:
    policy = RetryPolicy(max_attempts=3)
    assert policy.is_retryable(FailureCause.SANDBOX_FAILURE)
    assert policy.is_retryable(FailureCause.WORKER_FAILURE)
    assert not policy.is_retryable(FailureCause.ADAPTER_FAILURE)
    assert not policy.is_retryable(FailureCause.TIMEOUT)
    release = policy.action_for_failure(FailureCause.SANDBOX_FAILURE, attempt=1)
    assert release is RetryAction.RELEASE
    exhausted = policy.action_for_failure(FailureCause.SANDBOX_FAILURE, attempt=3)
    assert exhausted is RetryAction.ACK
    timeout = policy.action_for_failure(FailureCause.TIMEOUT, attempt=1)
    assert timeout is RetryAction.ACK


def test_run_until_idle_and_empty_claim() -> None:
    worker, queue, _cancel, _lives = _runtime()
    assert worker.run_once(block=False) is None
    queue.enqueue(RunId("a"))
    queue.enqueue(RunId("b"))
    results = worker.run_until_idle()
    assert len(results) == 2
    assert all(r.kind is EngineOutcomeKind.COMPLETED for r in results)
