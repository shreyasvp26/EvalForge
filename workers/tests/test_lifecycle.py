"""Comprehensive Run lifecycle orchestration tests (mocked ports only)."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest
from agent_eval_domain.common.ids import RunId
from agent_eval_domain.execution.run_status import RunStatus
from agent_eval_workers.lifecycle import (
    FailureCause,
    IllegalLifecycleTransition,
    LifecycleOrchestrator,
    LifecycleTrigger,
    OrchestrationPhase,
    RunLifecycle,
    domain_status_for,
)


@dataclass
class RecordingPorts:
    provisions: list[RunId] = field(default_factory=list)
    destroys: list[RunId] = field(default_factory=list)
    adapter_starts: list[RunId] = field(default_factory=list)
    adapter_runs: list[RunId] = field(default_factory=list)
    adapter_finishes: list[RunId] = field(default_factory=list)
    finals: list[RunId] = field(default_factory=list)
    scheduled: list[RunId] = field(default_factory=list)
    running: list[RunId] = field(default_factory=list)
    grading: list[RunId] = field(default_factory=list)
    completed: list[RunId] = field(default_factory=list)
    failed: list[tuple[RunId, FailureCause]] = field(default_factory=list)
    cancelled: list[RunId] = field(default_factory=list)

    def provision(self, run_id: RunId) -> None:
        self.provisions.append(run_id)

    def destroy(self, run_id: RunId) -> None:
        self.destroys.append(run_id)

    def start(self, run_id: RunId) -> None:
        self.adapter_starts.append(run_id)

    def run(self, run_id: RunId) -> None:
        self.adapter_runs.append(run_id)

    def finish(self, run_id: RunId) -> None:
        self.adapter_finishes.append(run_id)

    def persist_final(self, run_id: RunId) -> None:
        self.finals.append(run_id)

    def schedule(self, run_id: RunId) -> None:
        self.scheduled.append(run_id)

    def project_running(self, run_id: RunId) -> None:
        self.running.append(run_id)

    def project_grading(self, run_id: RunId) -> None:
        self.grading.append(run_id)

    def project_completed(self, run_id: RunId) -> None:
        self.completed.append(run_id)

    def project_failed(
        self, run_id: RunId, *, cause: FailureCause, detail: str | None = None
    ) -> None:
        del detail
        self.failed.append((run_id, cause))

    def project_cancelled(self, run_id: RunId) -> None:
        self.cancelled.append(run_id)


def _orchestrator() -> tuple[LifecycleOrchestrator, RecordingPorts]:
    ports = RecordingPorts()
    life = RunLifecycle(run_id=RunId("run-1"))
    orch = LifecycleOrchestrator(
        lifecycle=life,
        sandbox=ports,
        adapter=ports,
        events=ports,
        grading=ports,
        status=ports,
    )
    return orch, ports


def test_happy_path_reaches_completed() -> None:
    orch, ports = _orchestrator()
    transitions = orch.run_happy_path()
    assert orch.lifecycle.phase is OrchestrationPhase.COMPLETED
    assert orch.lifecycle.is_terminal
    assert orch.lifecycle.domain_status is RunStatus.COMPLETED
    assert [t.to_phase for t in transitions][-1] is OrchestrationPhase.COMPLETED
    assert ports.running == [RunId("run-1")]
    assert ports.provisions == [RunId("run-1")]
    assert ports.adapter_starts == [RunId("run-1")]
    assert ports.adapter_runs == [RunId("run-1")]
    assert ports.adapter_finishes == [RunId("run-1")]
    assert ports.finals == [RunId("run-1")]
    assert ports.scheduled == [RunId("run-1")]
    assert ports.grading == [RunId("run-1")]
    assert ports.completed == [RunId("run-1")]
    assert domain_status_for(OrchestrationPhase.GRADING_SCHEDULED) is RunStatus.GRADING


def test_illegal_transition_fails_immediately() -> None:
    life = RunLifecycle(run_id=RunId("run-1"))
    with pytest.raises(IllegalLifecycleTransition):
        life.apply(LifecycleTrigger.SANDBOX_READY)
    assert life.phase is OrchestrationPhase.QUEUED
    assert life.history == []


def test_terminal_rejects_further_triggers() -> None:
    orch, _ports = _orchestrator()
    orch.run_happy_path()
    with pytest.raises(IllegalLifecycleTransition):
        orch.apply(LifecycleTrigger.CLAIM)


@pytest.mark.parametrize(
    ("advance_to", "trigger", "cause"),
    [
        (
            OrchestrationPhase.SANDBOX_PROVISIONING,
            LifecycleTrigger.SANDBOX_FAILED,
            FailureCause.SANDBOX_FAILURE,
        ),
        (
            OrchestrationPhase.EXECUTION_STREAMING,
            LifecycleTrigger.ADAPTER_FAILED,
            FailureCause.ADAPTER_FAILURE,
        ),
        (
            OrchestrationPhase.EXECUTION_STREAMING,
            LifecycleTrigger.TIMEOUT,
            FailureCause.TIMEOUT,
        ),
        (
            OrchestrationPhase.SANDBOX_PROVISIONING,
            LifecycleTrigger.RESOURCE_EXHAUSTED,
            FailureCause.RESOURCE_EXHAUSTION,
        ),
        (
            OrchestrationPhase.CLAIMED,
            LifecycleTrigger.WORKER_FAILED,
            FailureCause.WORKER_FAILURE,
        ),
    ],
)
def test_failure_paths(
    advance_to: OrchestrationPhase,
    trigger: LifecycleTrigger,
    cause: FailureCause,
) -> None:
    orch, ports = _orchestrator()
    _advance_until(orch, advance_to)
    orch.apply(trigger)
    assert orch.lifecycle.phase is OrchestrationPhase.FAILED
    assert orch.lifecycle.failure_cause is cause
    assert orch.lifecycle.domain_status is RunStatus.FAILED
    assert ports.failed == [(RunId("run-1"), cause)]
    assert ports.destroys == [RunId("run-1")]


def test_cancellation_from_queued() -> None:
    orch, ports = _orchestrator()
    orch.apply(LifecycleTrigger.CANCEL)
    assert orch.lifecycle.phase is OrchestrationPhase.CANCELLED
    assert orch.lifecycle.domain_status is RunStatus.CANCELLED
    assert ports.cancelled == [RunId("run-1")]
    assert ports.destroys == [RunId("run-1")]


def test_cancellation_during_streaming() -> None:
    orch, ports = _orchestrator()
    _advance_until(orch, OrchestrationPhase.EXECUTION_STREAMING)
    orch.apply(LifecycleTrigger.CANCEL)
    assert orch.lifecycle.phase is OrchestrationPhase.CANCELLED
    assert ports.cancelled == [RunId("run-1")]


def test_grading_schedule_trigger() -> None:
    orch, ports = _orchestrator()
    _advance_until(orch, OrchestrationPhase.FINAL_EVENT_PERSISTENCE)
    orch.apply(LifecycleTrigger.FINALS_PERSISTED)
    assert orch.lifecycle.phase is OrchestrationPhase.GRADING_SCHEDULED
    assert ports.scheduled == [RunId("run-1")]
    assert ports.grading == [RunId("run-1")]
    assert orch.lifecycle.domain_status is RunStatus.GRADING


def test_timeout_illegal_before_work_starts() -> None:
    life = RunLifecycle(run_id=RunId("run-1"))
    life.apply(LifecycleTrigger.CLAIM)
    with pytest.raises(IllegalLifecycleTransition):
        life.apply(LifecycleTrigger.TIMEOUT)


def test_adapter_failure_illegal_before_adapter_starts() -> None:
    life = RunLifecycle(run_id=RunId("run-1"))
    life.apply(LifecycleTrigger.CLAIM)
    with pytest.raises(IllegalLifecycleTransition):
        life.apply(LifecycleTrigger.ADAPTER_FAILED)


def test_skip_to_grading_is_illegal() -> None:
    life = RunLifecycle(run_id=RunId("run-1"))
    with pytest.raises(IllegalLifecycleTransition):
        life.apply(LifecycleTrigger.GRADING_FINISHED)


def test_domain_mapping_covers_every_phase() -> None:
    for phase in OrchestrationPhase:
        assert domain_status_for(phase) in set(RunStatus)


def test_cancel_from_grading_scheduled() -> None:
    orch, ports = _orchestrator()
    _advance_until(orch, OrchestrationPhase.GRADING_SCHEDULED)
    orch.apply(LifecycleTrigger.CANCEL)
    assert orch.lifecycle.phase is OrchestrationPhase.CANCELLED
    assert ports.cancelled == [RunId("run-1")]


def test_completed_is_terminal() -> None:
    life = RunLifecycle(run_id=RunId("run-1"))
    for trigger in (
        LifecycleTrigger.CLAIM,
        LifecycleTrigger.BEGIN_SANDBOX_PROVISIONING,
        LifecycleTrigger.SANDBOX_READY,
        LifecycleTrigger.START_ADAPTER,
        LifecycleTrigger.ADAPTER_STARTED,
        LifecycleTrigger.ADAPTER_FINISHED,
        LifecycleTrigger.PERSIST_FINAL_EVENTS,
        LifecycleTrigger.FINALS_PERSISTED,
        LifecycleTrigger.GRADING_FINISHED,
    ):
        life.apply(trigger)
    assert life.phase is OrchestrationPhase.COMPLETED
    assert life.is_terminal
    assert life.domain_status is RunStatus.COMPLETED


def _advance_until(orch: LifecycleOrchestrator, target: OrchestrationPhase) -> None:
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
    for trigger in sequence:
        if orch.lifecycle.phase is target:
            return
        orch.apply(trigger)
    if orch.lifecycle.phase is not target:
        msg = f"Could not reach {target}; stopped at {orch.lifecycle.phase}"
        raise AssertionError(msg)
