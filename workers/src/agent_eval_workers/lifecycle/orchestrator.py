"""Lifecycle orchestrator — sequences port invocations around validated transitions.

Ports are interfaces only. No Adapter translation, grading, or Infrastructure
I/O is implemented here.
"""

from __future__ import annotations

from dataclasses import dataclass

from agent_eval_workers.lifecycle.machine import RunLifecycle
from agent_eval_workers.lifecycle.phases import OrchestrationPhase
from agent_eval_workers.lifecycle.ports import (
    AdapterPort,
    EventPipelinePort,
    GradingSchedulerPort,
    RunStatusPort,
    SandboxPort,
)
from agent_eval_workers.lifecycle.transitions import LifecycleTransition
from agent_eval_workers.lifecycle.triggers import LifecycleTrigger


@dataclass(slots=True)
class LifecycleOrchestrator:
    """Coordinates ports around the RunLifecycle state machine."""

    lifecycle: RunLifecycle
    sandbox: SandboxPort
    adapter: AdapterPort
    events: EventPipelinePort
    grading: GradingSchedulerPort
    status: RunStatusPort

    @property
    def phase(self) -> OrchestrationPhase:
        return self.lifecycle.phase

    @property
    def is_terminal(self) -> bool:
        return self.lifecycle.is_terminal

    def apply(self, trigger: LifecycleTrigger) -> LifecycleTransition:
        """Validate transition, then invoke the port appropriate to the trigger."""
        run_id = self.lifecycle.run_id
        transition = self.lifecycle.apply(trigger)

        if trigger is LifecycleTrigger.CLAIM:
            self.status.project_running(run_id)
        elif trigger is LifecycleTrigger.BEGIN_SANDBOX_PROVISIONING:
            self.sandbox.provision(run_id)
        elif trigger is LifecycleTrigger.START_ADAPTER:
            self.adapter.start(run_id)
        elif trigger is LifecycleTrigger.ADAPTER_STARTED:
            # Enter Execution Streaming: Adapter runs and streams continuously.
            self.adapter.run(run_id)
        elif trigger is LifecycleTrigger.ADAPTER_FINISHED:
            self.adapter.finish(run_id)
        elif trigger is LifecycleTrigger.PERSIST_FINAL_EVENTS:
            self.events.persist_final(run_id)
        elif trigger is LifecycleTrigger.FINALS_PERSISTED:
            self.grading.schedule(run_id)
            self.status.project_grading(run_id)
        elif trigger is LifecycleTrigger.GRADING_FINISHED:
            self.status.project_completed(run_id)
        elif transition.to_phase is OrchestrationPhase.FAILED:
            assert transition.failure_cause is not None
            self.sandbox.destroy(run_id)
            self.status.project_failed(run_id, cause=transition.failure_cause)
        elif transition.to_phase is OrchestrationPhase.CANCELLED:
            self.sandbox.destroy(run_id)
            self.status.project_cancelled(run_id)

        return transition

    def run_happy_path(self) -> list[LifecycleTransition]:
        """Drive the full happy-path trigger sequence (tests / local smoke)."""
        sequence = (
            LifecycleTrigger.CLAIM,
            LifecycleTrigger.BEGIN_SANDBOX_PROVISIONING,
            LifecycleTrigger.SANDBOX_READY,
            LifecycleTrigger.START_ADAPTER,
            LifecycleTrigger.ADAPTER_STARTED,
            LifecycleTrigger.ADAPTER_FINISHED,
            LifecycleTrigger.PERSIST_FINAL_EVENTS,
            LifecycleTrigger.FINALS_PERSISTED,
            LifecycleTrigger.GRADING_FINISHED,
        )
        return [self.apply(trigger) for trigger in sequence]
