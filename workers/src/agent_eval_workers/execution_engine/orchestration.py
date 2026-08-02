"""Compose Execution Engine orchestration with mocked subsystem ports.

This is the Phase 5 wiring layer: Worker hosts Engine; Engine drives
LifecycleOrchestrator; ports are mock Sandbox / Adapter / Grader / pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agent_eval_application.common.actor import Actor
from agent_eval_domain.common.ids import RunId

from agent_eval_workers.cancellation.registry import InMemoryCancellationRegistry
from agent_eval_workers.checkpoints.manager import CheckpointManager
from agent_eval_workers.checkpoints.memory import InMemoryCheckpointStore
from agent_eval_workers.clock import FakeClock, SystemClock
from agent_eval_workers.event_pipeline.pipeline import EventPersistencePipeline
from agent_eval_workers.event_pipeline.projector import ProjectionHub
from agent_eval_workers.execution_engine.lifecycle_driver import LifecycleDriver
from agent_eval_workers.lifecycle.machine import RunLifecycle
from agent_eval_workers.lifecycle.orchestrator import LifecycleOrchestrator
from agent_eval_workers.lifecycle.phases import OrchestrationPhase
from agent_eval_workers.mocks.adapter import MockAdapter
from agent_eval_workers.mocks.event_writer import InMemoryEventWriter
from agent_eval_workers.mocks.grader import MockGrader
from agent_eval_workers.mocks.grading_scheduler import MockGradingScheduler
from agent_eval_workers.mocks.sandbox import MockSandbox
from agent_eval_workers.mocks.status import RecordingRunStatus
from agent_eval_workers.worker.memory_queue import InMemoryWorkerQueue
from agent_eval_workers.worker.retry import RetryPolicy
from agent_eval_workers.worker.runtime import WorkerRuntime


@dataclass(slots=True)
class OrchestrationHarness:
    """Fully wired Worker + Engine stack with deterministic mocks."""

    queue: InMemoryWorkerQueue
    checkpoints: CheckpointManager
    cancellation: InMemoryCancellationRegistry
    writer: InMemoryEventWriter
    pipeline: EventPersistencePipeline
    sandbox: MockSandbox
    adapter: MockAdapter
    grading: MockGradingScheduler
    status: RecordingRunStatus
    worker: WorkerRuntime
    projections: ProjectionHub = field(default_factory=ProjectionHub)
    clock: FakeClock | SystemClock = field(default_factory=FakeClock)

    def enqueue(self, run_id: str) -> None:
        self.queue.enqueue(RunId(run_id))


def build_orchestration_harness(
    *,
    worker_id: str = "worker-1",
    graders: tuple[MockGrader, ...] | None = None,
    fail_sandbox: bool = False,
    fail_adapter: bool = False,
    emit_artifact: bool = True,
    batch_size: int = 1,
    max_attempts: int = 3,
    execution_timeout_seconds: float | None = None,
    clock: FakeClock | None = None,
) -> OrchestrationHarness:
    """Build an end-to-end orchestration stack (no external services)."""
    writer = InMemoryEventWriter()
    projections = ProjectionHub()
    pipeline = EventPersistencePipeline(
        writer=writer,
        actor=Actor(id="system-worker"),
        projections=projections,
        batch_size=batch_size,
    )
    sandbox = MockSandbox(fail_on_provision=fail_sandbox)
    adapter = MockAdapter(
        stream=pipeline,
        emit_artifact=emit_artifact,
        fail_on_run=fail_adapter,
    )
    default_graders = graders
    if default_graders is None:
        default_graders = (
            MockGrader(grader_id="g1", grader_version_id="gv1"),
            MockGrader(grader_id="g2", grader_version_id="gv2"),
        )
    grading = MockGradingScheduler(graders=default_graders)
    status = RecordingRunStatus()
    store = InMemoryCheckpointStore()
    checkpoints = CheckpointManager(store)
    cancellation = InMemoryCancellationRegistry()
    queue = InMemoryWorkerQueue()
    clock_impl: FakeClock | SystemClock = clock if clock is not None else FakeClock()

    def lifecycle_factory(run_id: RunId, phase: OrchestrationPhase) -> LifecycleDriver:
        return LifecycleOrchestrator(
            lifecycle=RunLifecycle(run_id=run_id, phase=phase),
            sandbox=sandbox,
            adapter=adapter,
            events=pipeline,
            grading=grading,
            status=status,
        )

    worker = WorkerRuntime(
        worker_id=worker_id,
        queue=queue,
        checkpoints=checkpoints,
        cancellation=cancellation,
        lifecycle_factory=lifecycle_factory,
        retry_policy=RetryPolicy(max_attempts=max_attempts),
        clock=clock_impl,
        execution_timeout_seconds=execution_timeout_seconds,
    )
    return OrchestrationHarness(
        queue=queue,
        checkpoints=checkpoints,
        cancellation=cancellation,
        writer=writer,
        pipeline=pipeline,
        sandbox=sandbox,
        adapter=adapter,
        grading=grading,
        status=status,
        worker=worker,
        projections=projections,
        clock=clock_impl,
    )


def rebuild_worker(
    harness: OrchestrationHarness,
    *,
    worker_id: str = "worker-2",
) -> WorkerRuntime:
    """Simulate Worker restart — same durable checkpoints / queue / mocks."""

    def lifecycle_factory(run_id: RunId, phase: OrchestrationPhase) -> LifecycleDriver:
        return LifecycleOrchestrator(
            lifecycle=RunLifecycle(run_id=run_id, phase=phase),
            sandbox=harness.sandbox,
            adapter=harness.adapter,
            events=harness.pipeline,
            grading=harness.grading,
            status=harness.status,
        )

    return WorkerRuntime(
        worker_id=worker_id,
        queue=harness.queue,
        checkpoints=harness.checkpoints,
        cancellation=harness.cancellation,
        lifecycle_factory=lifecycle_factory,
        retry_policy=harness.worker.retry_policy,
        clock=harness.clock,
        execution_timeout_seconds=harness.worker.execution_timeout_seconds,
    )
