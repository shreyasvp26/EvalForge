"""Worker runtime — operational chassis hosting the Execution Engine.

Owns queue leases, retries, heartbeats, shutdown, and checkpoint recovery.
Never decides the next Run lifecycle step — that is the Engine's job.
Never mutates Domain Run status directly — Engine → lifecycle → status port.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum

from agent_eval_domain.common.ids import RunId

from agent_eval_workers.cancellation.ports import CancellationPort
from agent_eval_workers.checkpoints.manager import CheckpointManager
from agent_eval_workers.clock import Clock, SystemClock
from agent_eval_workers.execution_engine.engine import ExecutionEngine, StepHook
from agent_eval_workers.execution_engine.lifecycle_driver import LifecycleDriver
from agent_eval_workers.execution_engine.results import EngineOutcomeKind, EngineResult
from agent_eval_workers.lifecycle.machine import RunLifecycle
from agent_eval_workers.lifecycle.phases import OrchestrationPhase
from agent_eval_workers.lifecycle.triggers import FailureCause
from agent_eval_workers.worker.queue import ClaimedTask, WorkerQueuePort
from agent_eval_workers.worker.retry import RetryAction, RetryPolicy


class WorkerState(StrEnum):
    IDLE = "idle"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"


LifecycleFactory = Callable[[RunId, OrchestrationPhase], LifecycleDriver]


@dataclass(slots=True)
class WorkerRuntime:
    """Process-level Worker: claim → recover → host Engine → ack/release."""

    worker_id: str
    queue: WorkerQueuePort
    checkpoints: CheckpointManager
    cancellation: CancellationPort
    lifecycle_factory: LifecycleFactory
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    clock: Clock = field(default_factory=SystemClock)
    execution_timeout_seconds: float | None = None
    visibility_extension_seconds: float = 30.0
    before_step: StepHook | None = None

    _state: WorkerState = field(default=WorkerState.IDLE, init=False)
    _stop_requested: bool = field(default=False, init=False)
    _current_task: ClaimedTask | None = field(default=None, init=False)

    @property
    def state(self) -> WorkerState:
        return self._state

    def request_stop(self) -> None:
        """Begin cooperative shutdown after the current task boundary."""
        self._stop_requested = True
        if self._state is WorkerState.IDLE:
            self._state = WorkerState.STOPPING

    def shutdown(self) -> None:
        """Mark the worker stopped (tests / process exit)."""
        self._stop_requested = True
        self._state = WorkerState.STOPPED

    def run_once(self, *, block: bool = False) -> EngineResult | None:
        """Claim at most one task and process it. ``None`` when the queue is idle."""
        if self._state is WorkerState.STOPPED:
            return None
        if self._stop_requested:
            self._state = WorkerState.STOPPED
            return None

        task = self.queue.claim(block=block)
        if task is None:
            return None

        self._current_task = task
        self._state = WorkerState.RUNNING
        try:
            result = self._process(task)
            self._settle(task, result)
            return result
        finally:
            self._current_task = None
            if self._stop_requested:
                self._state = WorkerState.STOPPED
            else:
                self._state = WorkerState.IDLE

    def run_until_idle(self, *, max_tasks: int | None = None) -> list[EngineResult]:
        """Drain available tasks without blocking (useful in tests)."""
        results: list[EngineResult] = []
        while max_tasks is None or len(results) < max_tasks:
            if self._stop_requested:
                self._state = WorkerState.STOPPED
                break
            result = self.run_once(block=False)
            if result is None:
                break
            results.append(result)
        return results

    def _process(self, task: ClaimedTask) -> EngineResult:
        checkpoint = self.checkpoints.restore(task.run_id)
        if checkpoint is not None and not checkpoint.is_resumable:
            return EngineResult(
                kind=EngineOutcomeKind.ALREADY_TERMINAL,
                phase=checkpoint.phase,
            )

        phase = (
            checkpoint.phase if checkpoint is not None else OrchestrationPhase.QUEUED
        )
        attempt = checkpoint.attempt if checkpoint is not None else 1
        lifecycle = self.lifecycle_factory(task.run_id, phase)

        engine = ExecutionEngine(
            lifecycle=lifecycle,
            checkpoints=self.checkpoints,
            cancellation=self.cancellation,
            clock=self.clock,
            run_id=task.run_id,
            attempt=attempt,
            execution_timeout_seconds=self.execution_timeout_seconds,
            on_progress=lambda: self._heartbeat(task),
            should_interrupt=lambda: self._stop_requested,
            before_step=self.before_step,
        )
        result = engine.execute()

        if result.kind is EngineOutcomeKind.RECOVERABLE_FAILURE:
            assert result.failure_cause is not None
            action = self.retry_policy.action_for_failure(
                result.failure_cause,
                attempt=attempt,
            )
            if action is RetryAction.RELEASE:
                # Persist resume marker and bump attempt for the next claim.
                resume = result.resume_phase or result.phase
                self.checkpoints.create(
                    task.run_id,
                    resume,
                    attempt=attempt + 1,
                )
                return result

            # Retries exhausted — finalize terminal Failed via the Engine.
            final_lifecycle = self.lifecycle_factory(task.run_id, result.phase)
            final_engine = ExecutionEngine(
                lifecycle=final_lifecycle,
                checkpoints=self.checkpoints,
                cancellation=self.cancellation,
                clock=self.clock,
                run_id=task.run_id,
                attempt=attempt,
            )
            return final_engine.finalize_failure(result.failure_cause)

        return result

    def _settle(self, task: ClaimedTask, result: EngineResult) -> None:
        if result.kind in {
            EngineOutcomeKind.COMPLETED,
            EngineOutcomeKind.CANCELLED,
            EngineOutcomeKind.FAILED,
            EngineOutcomeKind.ALREADY_TERMINAL,
        }:
            self.queue.ack(task)
            return

        if result.kind in {
            EngineOutcomeKind.RECOVERABLE_FAILURE,
            EngineOutcomeKind.INTERRUPTED,
        }:
            self.queue.release(task)
            return

        self.queue.release(task)

    def _heartbeat(self, task: ClaimedTask) -> None:
        self.queue.heartbeat(task)
        self.queue.extend_visibility(
            task,
            seconds=self.visibility_extension_seconds,
        )


def default_lifecycle_factory(
    run_id: RunId,
    phase: OrchestrationPhase,
) -> LifecycleDriver:
    """Build a plain ``RunLifecycle`` driver (no port side effects).

    Production wiring supplies a ``LifecycleOrchestrator``; tests often mock
    the factory entirely.
    """
    return RunLifecycle(run_id=run_id, phase=phase)


def classify_worker_failure(cause: FailureCause) -> RetryAction:
    """Convenience for introspection / tests."""
    return RetryPolicy().action_for_failure(cause, attempt=1)
