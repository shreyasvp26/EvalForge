"""Execution Engine — orchestration authority hosted inside a Worker.

Owns sequencing via the lifecycle. Does not own queue leases, retry budgets,
or process lifecycle — those remain Worker concerns.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from agent_eval_domain.common.ids import RunId

from agent_eval_workers.cancellation.ports import CancellationPort
from agent_eval_workers.checkpoints.manager import CheckpointManager
from agent_eval_workers.clock import Clock
from agent_eval_workers.execution_engine.errors import RecoverableExecutionError
from agent_eval_workers.execution_engine.lifecycle_driver import LifecycleDriver
from agent_eval_workers.execution_engine.results import EngineOutcomeKind, EngineResult
from agent_eval_workers.execution_engine.sequence import next_happy_path_trigger
from agent_eval_workers.lifecycle.errors import IllegalLifecycleTransition
from agent_eval_workers.lifecycle.phases import OrchestrationPhase, is_terminal_phase
from agent_eval_workers.lifecycle.triggers import FailureCause, LifecycleTrigger

StepHook = Callable[[LifecycleTrigger], None]


@dataclass(slots=True)
class ExecutionEngine:
    """Drive one Run's lifecycle with cooperative cancel / timeout checks."""

    lifecycle: LifecycleDriver
    checkpoints: CheckpointManager
    cancellation: CancellationPort
    clock: Clock
    run_id: RunId
    attempt: int = 1
    execution_timeout_seconds: float | None = None
    """Wall-clock budget from ``execute`` start; ``None`` disables monitoring."""

    on_progress: Callable[[], None] | None = None
    """Worker-supplied hook (heartbeat / visibility extension)."""

    should_interrupt: Callable[[], bool] | None = None
    """Worker shutdown / interruption probe."""

    before_step: StepHook | None = None
    """Optional hook before each happy-path trigger (tests / port wiring)."""

    def execute(self) -> EngineResult:
        """Advance orchestration until terminal, recoverable failure, or interrupt."""
        if is_terminal_phase(self.lifecycle.phase):
            return EngineResult(
                kind=EngineOutcomeKind.ALREADY_TERMINAL,
                phase=self.lifecycle.phase,
            )

        deadline: float | None = None
        if self.execution_timeout_seconds is not None:
            deadline = self.clock.monotonic() + self.execution_timeout_seconds

        self.checkpoints.create(
            self.run_id,
            self.lifecycle.phase,
            attempt=self.attempt,
        )

        while not self.lifecycle.is_terminal:
            if self.should_interrupt is not None and self.should_interrupt():
                return EngineResult(
                    kind=EngineOutcomeKind.INTERRUPTED,
                    phase=self.lifecycle.phase,
                    resume_phase=self.lifecycle.phase,
                )

            if self.cancellation.is_cancel_requested(self.run_id):
                self.lifecycle.apply(LifecycleTrigger.CANCEL)
                self.checkpoints.create(
                    self.run_id,
                    self.lifecycle.phase,
                    attempt=self.attempt,
                )
                return EngineResult(
                    kind=EngineOutcomeKind.CANCELLED,
                    phase=self.lifecycle.phase,
                )

            if deadline is not None and self.clock.monotonic() >= deadline:
                return self._apply_timeout()

            trigger = next_happy_path_trigger(self.lifecycle.phase)
            if trigger is None:
                return EngineResult(
                    kind=EngineOutcomeKind.RECOVERABLE_FAILURE,
                    phase=self.lifecycle.phase,
                    failure_cause=FailureCause.WORKER_FAILURE,
                    resume_phase=self.lifecycle.phase,
                )

            resume_before = self.lifecycle.phase
            try:
                if self.before_step is not None:
                    self.before_step(trigger)
                self.lifecycle.apply(trigger)
            except RecoverableExecutionError as exc:
                # ``phase`` is where finalize should apply; ``resume_phase`` is
                # the durable restart point for Worker retries.
                return EngineResult(
                    kind=EngineOutcomeKind.RECOVERABLE_FAILURE,
                    phase=self.lifecycle.phase,
                    failure_cause=exc.cause,
                    resume_phase=resume_before,
                )

            self.checkpoints.create(
                self.run_id,
                self.lifecycle.phase,
                attempt=self.attempt,
            )
            if self.on_progress is not None:
                self.on_progress()

        return self._result_for_terminal()

    def finalize_failure(self, cause: FailureCause) -> EngineResult:
        """Apply a terminal Failed transition after the Worker exhausts retries."""
        applied_cause = cause
        try:
            self.lifecycle.apply(_failure_trigger_for(cause))
        except IllegalLifecycleTransition:
            # Cause-specific trigger may be illegal at the resume phase; Worker
            # failure is legal for every failable orchestration stage.
            self.lifecycle.apply(LifecycleTrigger.WORKER_FAILED)
            applied_cause = FailureCause.WORKER_FAILURE
        self.checkpoints.create(
            self.run_id,
            self.lifecycle.phase,
            attempt=self.attempt,
        )
        return EngineResult(
            kind=EngineOutcomeKind.FAILED,
            phase=self.lifecycle.phase,
            failure_cause=applied_cause,
        )

    def _apply_timeout(self) -> EngineResult:
        phase = self.lifecycle.phase
        allowed = {
            OrchestrationPhase.SANDBOX_PROVISIONING,
            OrchestrationPhase.ADAPTER_STARTING,
            OrchestrationPhase.EXECUTION_STREAMING,
        }
        if phase in allowed:
            self.lifecycle.apply(LifecycleTrigger.TIMEOUT)
            self.checkpoints.create(
                self.run_id,
                self.lifecycle.phase,
                attempt=self.attempt,
            )
            return EngineResult(
                kind=EngineOutcomeKind.FAILED,
                phase=self.lifecycle.phase,
                failure_cause=FailureCause.TIMEOUT,
            )
        return EngineResult(
            kind=EngineOutcomeKind.RECOVERABLE_FAILURE,
            phase=phase,
            failure_cause=FailureCause.WORKER_FAILURE,
            resume_phase=phase,
        )

    def _result_for_terminal(self) -> EngineResult:
        phase = self.lifecycle.phase
        if phase is OrchestrationPhase.COMPLETED:
            return EngineResult(kind=EngineOutcomeKind.COMPLETED, phase=phase)
        if phase is OrchestrationPhase.CANCELLED:
            return EngineResult(kind=EngineOutcomeKind.CANCELLED, phase=phase)
        if phase is OrchestrationPhase.FAILED:
            return EngineResult(
                kind=EngineOutcomeKind.FAILED,
                phase=phase,
                failure_cause=FailureCause.WORKER_FAILURE,
            )
        return EngineResult(
            kind=EngineOutcomeKind.INTERRUPTED,
            phase=phase,
            resume_phase=phase,
        )


def _failure_trigger_for(cause: FailureCause) -> LifecycleTrigger:
    mapping = {
        FailureCause.ADAPTER_FAILURE: LifecycleTrigger.ADAPTER_FAILED,
        FailureCause.SANDBOX_FAILURE: LifecycleTrigger.SANDBOX_FAILED,
        FailureCause.WORKER_FAILURE: LifecycleTrigger.WORKER_FAILED,
        FailureCause.TIMEOUT: LifecycleTrigger.TIMEOUT,
        FailureCause.RESOURCE_EXHAUSTION: LifecycleTrigger.RESOURCE_EXHAUSTED,
    }
    return mapping[cause]
