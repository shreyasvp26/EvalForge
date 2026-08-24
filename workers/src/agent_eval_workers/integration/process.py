"""Process-level production composition for ``evalforge-worker``.

Wires Redis claim → LifecycleOrchestrator → DockerSandbox → ClaudeCodeAdapter →
pin-resolved objective graders → Application Run status / events / scores.

Test infrastructure (FakeDockerEngine, deterministic Claude stream) is selected
via env when a live Docker daemon / Claude CLI is unavailable — still through
the same production ports, never by fabricating Domain completion.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterator
from dataclasses import dataclass

from agent_eval_adapters.claude_code import ClaudeCodeAdapter
from agent_eval_adapters.sdk.adapter import Adapter
from agent_eval_adapters.sdk.models import RunMetadata
from agent_eval_application.common.actor import Actor
from agent_eval_application.queries.queries import GetRunQuery
from agent_eval_application.use_cases.grader import ListGraders
from agent_eval_application.use_cases.run import (
    CancelRun,
    CompleteRun,
    FailRun,
    GetRun,
    GetRunArtifacts,
    GetRunEvents,
    RecordArtifact,
    RecordExecutionEvent,
    RecordScore,
    StartGrading,
    StartRun,
)
from agent_eval_domain.common.ids import RunId
from agent_eval_sandbox.docker.engine import DockerPyEngine
from agent_eval_sandbox.docker.fake import FakeDockerEngine
from agent_eval_sandbox.docker.sandbox import DockerSandbox
from agent_eval_sandbox.manager import SandboxManager
from agent_eval_sandbox.ports import DockerEngine
from agent_eval_shared.log import get_logger

from agent_eval_workers.cancellation.registry import InMemoryCancellationRegistry
from agent_eval_workers.checkpoints.manager import CheckpointManager
from agent_eval_workers.checkpoints.memory import InMemoryCheckpointStore
from agent_eval_workers.clock import SystemClock
from agent_eval_workers.event_pipeline.pipeline import (
    EventPersistencePipeline,
    UseCaseEventWriter,
)
from agent_eval_workers.event_pipeline.projector import ProjectionHub
from agent_eval_workers.execution_engine.lifecycle_driver import LifecycleDriver
from agent_eval_workers.integration.adapter_bridge import SdkAdapterBridge
from agent_eval_workers.integration.composition import default_claude_factory
from agent_eval_workers.integration.grader_resolver import PinBasedGraderResolver
from agent_eval_workers.integration.grading_scheduler import GraderSdkScheduler
from agent_eval_workers.integration.registry import RunSandboxRegistry
from agent_eval_workers.integration.run_status import ApplicationRunStatus
from agent_eval_workers.integration.sandbox_adapter import ManagedSandboxAdapter
from agent_eval_workers.integration.worker_auth import WorkerAuthorization
from agent_eval_workers.lifecycle.machine import RunLifecycle
from agent_eval_workers.lifecycle.orchestrator import LifecycleOrchestrator
from agent_eval_workers.lifecycle.phases import OrchestrationPhase
from agent_eval_workers.worker.queue import WorkerQueuePort
from agent_eval_workers.worker.retry import RetryPolicy
from agent_eval_workers.worker.runtime import LifecycleFactory, WorkerRuntime

logger = get_logger("agent_eval_workers.integration.process")

AdapterFactory = Callable[[], Adapter]
StreamSource = Callable[[object], Iterator[str]]


@dataclass(slots=True)
class ProductionWorkerBundle:
    """Assembled process-level worker + shared ports (for tests / introspection)."""

    worker: WorkerRuntime
    cancellation: InMemoryCancellationRegistry
    sandbox: ManagedSandboxAdapter
    adapter: SdkAdapterBridge
    grading: GraderSdkScheduler
    status: ApplicationRunStatus
    docker_engine: DockerEngine
    actor: Actor
    sandbox_mode: str
    adapter_mode: str


def select_docker_engine(*, mode: str | None = None) -> tuple[DockerEngine, str]:
    """Choose Docker backend: ``docker`` | ``fake`` | ``auto`` (default)."""
    resolved = (mode or os.environ.get("WORKER_SANDBOX_ENGINE", "auto")).strip().lower()
    if resolved == "fake":
        logger.warning(
            "worker_sandbox_engine_fake",
            detail="Using FakeDockerEngine (test/local infrastructure)",
        )
        return FakeDockerEngine(), "fake"
    if resolved == "docker":
        return DockerPyEngine.from_env(), "docker"
    # auto
    try:
        engine = DockerPyEngine.from_env()
        # Cheap probe — list containers (or ping). Fail closed to fake.
        engine.client.ping()
        return engine, "docker"
    except Exception as exc:  # noqa: BLE001 — intentional fallback
        logger.warning(
            "worker_sandbox_engine_fallback_fake",
            error=str(exc),
            detail="Docker unavailable; FakeDockerEngine selected for local execution",
        )
        return FakeDockerEngine(), "fake"


def select_adapter_factory(*, mode: str | None = None) -> tuple[AdapterFactory, str]:
    """Choose Claude adapter mode: ``deterministic`` (injected stream) | ``claude``."""
    resolved = (
        (mode or os.environ.get("WORKER_ADAPTER_MODE", "deterministic")).strip().lower()
    )
    if resolved in {"claude", "live", "cli"}:
        logger.info("worker_adapter_mode_claude_cli")

        def live_factory() -> Adapter:
            return ClaudeCodeAdapter()

        return live_factory, "claude"
    # deterministic — real ClaudeCodeAdapter through injected NDJSON stream
    logger.info(
        "worker_adapter_mode_deterministic",
        detail="ClaudeCodeAdapter with injected stream (Phase 1 canonical path)",
    )
    return default_claude_factory(), "deterministic"


def build_production_lifecycle_factory(
    *,
    uow_factory: object,
    ids: object,
    events: object,
    docker_engine: DockerEngine,
    actor: Actor | None = None,
    auth: object | None = None,
    adapter_factory: AdapterFactory | None = None,
    cancellation: InMemoryCancellationRegistry | None = None,
) -> tuple[
    LifecycleFactory,
    ManagedSandboxAdapter,
    SdkAdapterBridge,
    GraderSdkScheduler,
    ApplicationRunStatus,
    InMemoryCancellationRegistry,
]:
    """Construct the LifecycleOrchestrator factory used by WorkerRuntime."""
    system_actor = actor or Actor(id="system-worker")
    worker_auth = auth or WorkerAuthorization(system_actor_id=system_actor.id)
    cancel = cancellation or InMemoryCancellationRegistry()
    sandbox_registry = RunSandboxRegistry()
    manager = SandboxManager(runtime=DockerSandbox(engine=docker_engine))
    sandbox = ManagedSandboxAdapter(manager=manager, registry=sandbox_registry)

    writer = UseCaseEventWriter(
        record_event_uc=RecordExecutionEvent(uow_factory, worker_auth, events),
        record_artifact_uc=RecordArtifact(uow_factory, ids, worker_auth, events),
    )
    pipeline = EventPersistencePipeline(
        writer=writer,
        actor=system_actor,
        projections=ProjectionHub(),
        batch_size=1,
    )

    get_run = GetRun(uow_factory, worker_auth)

    def run_metadata_factory(run_id: RunId) -> RunMetadata:
        dto = get_run.execute(GetRunQuery(actor=system_actor, run_id=run_id.value))
        return RunMetadata(
            run_id=dto.id,
            agent_version_id=dto.pins.agent_version_id,
            adapter_version_id=dto.pins.adapter_version_id,
            prompt_version_id=dto.pins.prompt_version_id,
            case_version_id=dto.pins.case_version_id,
        )

    factory = adapter_factory or default_claude_factory()
    adapter = SdkAdapterBridge(
        stream=pipeline,
        sandboxes=sandbox_registry,
        manager=manager,
        adapter_factory=factory,
        cancellation=cancel,
        run_metadata_factory=run_metadata_factory,
    )

    resolver = PinBasedGraderResolver(
        actor=system_actor,
        get_run=get_run,
        list_graders=ListGraders(uow_factory, worker_auth),
    )
    grading = GraderSdkScheduler(
        actor=system_actor,
        get_run=get_run,
        get_events=GetRunEvents(uow_factory, worker_auth),
        get_artifacts=GetRunArtifacts(uow_factory, worker_auth),
        record_score=RecordScore(uow_factory, ids, worker_auth, events),
        grader_resolver=resolver.resolve,
    )

    status = ApplicationRunStatus(
        actor=system_actor,
        sandbox_registry=sandbox_registry,
        start_run=StartRun(uow_factory, worker_auth, events),
        start_grading=StartGrading(uow_factory, worker_auth, events),
        complete_run=CompleteRun(uow_factory, worker_auth, events),
        fail_run=FailRun(uow_factory, worker_auth, events),
        cancel_run=CancelRun(uow_factory, worker_auth, events),
    )

    def lifecycle_factory(run_id: RunId, phase: OrchestrationPhase) -> LifecycleDriver:
        return LifecycleOrchestrator(
            lifecycle=RunLifecycle(run_id=run_id, phase=phase),
            sandbox=sandbox,
            adapter=adapter,
            events=pipeline,
            grading=grading,
            status=status,
        )

    return lifecycle_factory, sandbox, adapter, grading, status, cancel


def build_production_worker(
    *,
    queue: WorkerQueuePort,
    uow_factory: object,
    ids: object,
    events: object,
    worker_id: str = "worker-1",
    docker_engine: DockerEngine | None = None,
    adapter_factory: AdapterFactory | None = None,
    actor: Actor | None = None,
    auth: object | None = None,
    max_attempts: int = 3,
    execution_timeout_seconds: float | None = None,
    sandbox_mode: str | None = None,
    adapter_mode: str | None = None,
) -> ProductionWorkerBundle:
    """Wire a production WorkerRuntime against an injected WorkerQueuePort."""
    system_actor = actor or Actor(id=os.environ.get("WORKER_ACTOR_ID", "system-worker"))
    if docker_engine is None:
        engine, resolved_sandbox = select_docker_engine(mode=sandbox_mode)
    else:
        engine, resolved_sandbox = docker_engine, sandbox_mode or "injected"

    if adapter_factory is None:
        factory, resolved_adapter = select_adapter_factory(mode=adapter_mode)
    else:
        factory, resolved_adapter = adapter_factory, adapter_mode or "injected"

    (
        lifecycle_factory,
        sandbox,
        adapter,
        grading,
        status,
        cancellation,
    ) = build_production_lifecycle_factory(
        uow_factory=uow_factory,
        ids=ids,
        events=events,
        docker_engine=engine,
        actor=system_actor,
        auth=auth,
        adapter_factory=factory,
    )

    worker = WorkerRuntime(
        worker_id=worker_id,
        queue=queue,
        checkpoints=CheckpointManager(InMemoryCheckpointStore()),
        cancellation=cancellation,
        lifecycle_factory=lifecycle_factory,
        retry_policy=RetryPolicy(max_attempts=max_attempts),
        clock=SystemClock(),
        execution_timeout_seconds=execution_timeout_seconds,
    )
    return ProductionWorkerBundle(
        worker=worker,
        cancellation=cancellation,
        sandbox=sandbox,
        adapter=adapter,
        grading=grading,
        status=status,
        docker_engine=engine,
        actor=system_actor,
        sandbox_mode=resolved_sandbox,
        adapter_mode=resolved_adapter,
    )
