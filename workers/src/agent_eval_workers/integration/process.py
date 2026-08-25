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
from typing import Protocol

from agent_eval_adapters.claude_code import ClaudeCodeAdapter
from agent_eval_adapters.sdk.adapter import Adapter
from agent_eval_adapters.sdk.models import RunMetadata
from agent_eval_application.common.actor import Actor
from agent_eval_application.queries.queries import GetRunQuery
from agent_eval_application.use_cases.agent import ListAdapters
from agent_eval_application.use_cases.case import ListCasesByProject
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
    RecordRunTelemetry,
    RecordScore,
    StartGrading,
    StartRun,
)
from agent_eval_domain.common.ids import RunId
from agent_eval_sandbox.docker.engine import DockerPyEngine
from agent_eval_sandbox.docker.fake import FakeDockerEngine
from agent_eval_sandbox.docker.sandbox import DockerSandbox
from agent_eval_sandbox.manager import SandboxManager
from agent_eval_sandbox.models import ExecutionRequest
from agent_eval_sandbox.ports import DockerEngine
from agent_eval_shared.log import get_logger

from agent_eval_workers.cancellation.ports import CancellationPort
from agent_eval_workers.cancellation.registry import InMemoryCancellationRegistry
from agent_eval_workers.checkpoints.manager import CheckpointManager
from agent_eval_workers.checkpoints.memory import InMemoryCheckpointStore
from agent_eval_workers.clock import SystemClock
from agent_eval_workers.event_pipeline.pipeline import (
    EventPersistencePipeline,
    UseCaseEventWriter,
)
from agent_eval_workers.event_pipeline.projector import ProjectionHub
from agent_eval_workers.execution_engine.errors import RecoverableExecutionError
from agent_eval_workers.execution_engine.lifecycle_driver import LifecycleDriver
from agent_eval_workers.integration.adapter_bridge import SdkAdapterBridge
from agent_eval_workers.integration.adapter_registry import (
    AdapterResolutionError,
    PinnedAdapterResolver,
    resolve_adapter_mode,
)
from agent_eval_workers.integration.composition import default_claude_factory
from agent_eval_workers.integration.grader_resolver import PinBasedGraderResolver
from agent_eval_workers.integration.grading_scheduler import GraderSdkScheduler
from agent_eval_workers.integration.judge_wiring import (
    build_judge_provider,
    make_rubric_factory,
)
from agent_eval_workers.integration.prompt_resolver import PinnedPromptResolver
from agent_eval_workers.integration.redis_event_projector import (
    RedisEventFanoutProjector,
)
from agent_eval_workers.integration.registry import RunSandboxRegistry
from agent_eval_workers.integration.repository_materializer import (
    SandboxRepositoryPreparer,
)
from agent_eval_workers.integration.run_status import ApplicationRunStatus
from agent_eval_workers.integration.sandbox_adapter import (
    ManagedSandboxAdapter,
    sandbox_environment_from_allowlist,
)
from agent_eval_workers.integration.worker_auth import WorkerAuthorization
from agent_eval_workers.integration.workspace_grader import WorkspaceExpectedFileProbe
from agent_eval_workers.lifecycle.machine import RunLifecycle
from agent_eval_workers.lifecycle.orchestrator import LifecycleOrchestrator
from agent_eval_workers.lifecycle.phases import OrchestrationPhase
from agent_eval_workers.lifecycle.triggers import FailureCause
from agent_eval_workers.worker.queue import WorkerQueuePort
from agent_eval_workers.worker.retry import RetryPolicy
from agent_eval_workers.worker.runtime import LifecycleFactory, WorkerRuntime

logger = get_logger("agent_eval_workers.integration.process")

AdapterFactory = Callable[[], Adapter]
StreamSource = Callable[[object], Iterator[str]]


class _ArtifactStore(Protocol):
    def put(self, key: str, data: bytes, *, content_type: str) -> object: ...


@dataclass(slots=True)
class ProductionWorkerBundle:
    """Assembled process-level worker + shared ports (for tests / introspection)."""

    worker: WorkerRuntime
    cancellation: CancellationPort
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
        logger.info("worker_sandbox_engine_docker")
        return DockerPyEngine.from_env(), "docker"
    # auto
    try:
        engine = DockerPyEngine.from_env()
        # Cheap probe — list containers (or ping). Fail closed to fake.
        engine.client.ping()
        logger.info("worker_sandbox_engine_auto_docker")
        return engine, "docker"
    except Exception as exc:  # noqa: BLE001 — intentional fallback
        logger.warning(
            "worker_sandbox_engine_fallback_fake",
            error=str(exc),
            detail="Docker unavailable; FakeDockerEngine selected for local execution",
        )
        return FakeDockerEngine(), "fake"


def select_adapter_factory(*, mode: str | None = None) -> tuple[AdapterFactory, str]:
    """Legacy composition helper — prefers pin resolution in production.

    Kept for tests that call ``select_adapter_factory`` directly. Production
    workers resolve adapters from Run pins via ``PinnedAdapterResolver``.
    ``deterministic`` is synthetic development/test execution only.
    """
    resolved = resolve_adapter_mode(mode)
    if resolved == "live":
        logger.info(
            "worker_adapter_mode_live",
            detail="Live mode selected; pin resolution still required at run time",
        )

        def live_factory() -> Adapter:
            return ClaudeCodeAdapter()

        return live_factory, "live"
    logger.info(
        "worker_adapter_mode_deterministic",
        detail=(
            "Synthetic development/test execution via injected NDJSON stream "
            "(not a live coding agent)"
        ),
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
    adapter_mode: str | None = None,
    cancellation: CancellationPort | None = None,
    object_storage: _ArtifactStore | None = None,
    event_fanout: object | None = None,
) -> tuple[
    LifecycleFactory,
    ManagedSandboxAdapter,
    SdkAdapterBridge,
    GraderSdkScheduler,
    ApplicationRunStatus,
    CancellationPort,
]:
    """Construct the LifecycleOrchestrator factory used by WorkerRuntime."""
    system_actor = actor or Actor(id="system-worker")
    worker_auth = auth or WorkerAuthorization(system_actor_id=system_actor.id)
    cancel: CancellationPort = cancellation or InMemoryCancellationRegistry()
    sandbox_registry = RunSandboxRegistry()
    manager = SandboxManager(runtime=DockerSandbox(engine=docker_engine))
    sandbox = ManagedSandboxAdapter(manager=manager, registry=sandbox_registry)

    get_run = GetRun(uow_factory, worker_auth)
    list_cases = ListCasesByProject(uow_factory, worker_auth)
    repo_preparer = SandboxRepositoryPreparer(
        actor=system_actor,
        get_run=get_run,
        list_cases=list_cases,
        manager=manager,
        sandboxes=sandbox_registry,
    )

    verify_enabled = os.environ.get("WORKER_SANDBOX_VERIFY", "0").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    def _after_provision(run_id: RunId) -> None:
        if verify_enabled:
            handle = sandbox.handle_for(run_id)
            result = manager.execute(
                handle,
                ExecutionRequest(command=("true",), timeout_seconds=15.0),
            )
            if result.timed_out or result.exit_code != 0:
                raise RecoverableExecutionError(
                    f"Sandbox workspace verify failed for {run_id.value} "
                    f"(exit={result.exit_code}, timed_out={result.timed_out})",
                    cause=FailureCause.SANDBOX_FAILURE,
                )
        repo_preparer(run_id)

    sandbox.after_provision = _after_provision

    writer = UseCaseEventWriter(
        record_event_uc=RecordExecutionEvent(uow_factory, worker_auth, events),
        record_artifact_uc=RecordArtifact(uow_factory, ids, worker_auth, events),
    )
    projections = ProjectionHub()
    if event_fanout is not None:
        projections.subscribe(RedisEventFanoutProjector(fanout=event_fanout))
    pipeline = EventPersistencePipeline(
        writer=writer,
        actor=system_actor,
        projections=projections,
        batch_size=1,
    )

    list_adapters = ListAdapters(uow_factory, worker_auth)
    prompt_resolver = PinnedPromptResolver(
        actor=system_actor,
        get_run=get_run,
        list_cases=list_cases,
    )
    pinned_adapter_resolver = PinnedAdapterResolver(
        actor=system_actor,
        get_run=get_run,
        list_adapters=list_adapters,
        mode=adapter_mode,
    )

    def run_metadata_factory(run_id: RunId) -> RunMetadata:
        dto = get_run.execute(GetRunQuery(actor=system_actor, run_id=run_id.value))
        return RunMetadata(
            run_id=dto.id,
            agent_version_id=dto.pins.agent_version_id,
            adapter_version_id=dto.pins.adapter_version_id,
            prompt_version_id=dto.pins.prompt_version_id,
            case_version_id=dto.pins.case_version_id,
        )

    def resolve_adapter_factory(run_id: RunId) -> AdapterFactory:
        try:
            return pinned_adapter_resolver.resolve_factory(run_id)
        except AdapterResolutionError as exc:
            raise RecoverableExecutionError(
                str(exc),
                cause=FailureCause.ADAPTER_FAILURE,
            ) from exc

    # Injected factory overrides pin resolution (tests / explicit composition).
    # When absent, resolve from the Run's pinned Adapter Version at start time.
    fallback_factory = adapter_factory or default_claude_factory()
    adapter = SdkAdapterBridge(
        stream=pipeline,
        sandboxes=sandbox_registry,
        manager=manager,
        adapter_factory=fallback_factory,
        adapter_factory_resolver=(
            None if adapter_factory is not None else resolve_adapter_factory
        ),
        cancellation=cancel,  # type: ignore[arg-type]
        object_storage=object_storage,
        environment=sandbox_environment_from_allowlist(),
        run_metadata_factory=run_metadata_factory,
        prompt_factory=prompt_resolver.resolve,
        working_directory_factory=lambda rid: repo_preparer.workspaces.get(
            rid.value, "/workspace"
        ),
    )

    resolver = PinBasedGraderResolver(
        actor=system_actor,
        get_run=get_run,
        list_graders=ListGraders(uow_factory, worker_auth),
    )
    judge = build_judge_provider()
    if judge is not None:
        resolver.rubric_factory = make_rubric_factory(judge)
    else:
        logger.info(
            "judge_provider_unconfigured",
            detail=(
                "Rubric grader pins will fail closed until JUDGE_PROVIDER "
                "(or a supported judge API key) is configured"
            ),
        )
    workspace_probe = WorkspaceExpectedFileProbe(
        manager=manager,
        sandboxes=sandbox_registry,
        working_directory_factory=lambda rid: repo_preparer.workspaces.get(
            rid.value, "/workspace"
        ),
    )
    grading = GraderSdkScheduler(
        actor=system_actor,
        get_run=get_run,
        get_events=GetRunEvents(uow_factory, worker_auth),
        get_artifacts=GetRunArtifacts(uow_factory, worker_auth),
        record_score=RecordScore(uow_factory, ids, worker_auth, events),
        grader_resolver=resolver.resolve,
        workspace_probe=workspace_probe.verify,
        workspace_results_getter=workspace_probe.workspace_results,
    )

    status = ApplicationRunStatus(
        actor=system_actor,
        sandbox_registry=sandbox_registry,
        start_run=StartRun(uow_factory, worker_auth, events),
        start_grading=StartGrading(uow_factory, worker_auth, events),
        complete_run=CompleteRun(uow_factory, worker_auth, events),
        fail_run=FailRun(uow_factory, worker_auth, events),
        cancel_run=CancelRun(uow_factory, worker_auth, events),
        record_telemetry=RecordRunTelemetry(uow_factory, worker_auth, events),
        event_fanout=event_fanout,
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
    cancellation: CancellationPort | None = None,
    object_storage: _ArtifactStore | None = None,
    event_fanout: object | None = None,
) -> ProductionWorkerBundle:
    """Wire a production WorkerRuntime against an injected WorkerQueuePort."""
    system_actor = actor or Actor(id=os.environ.get("WORKER_ACTOR_ID", "system-worker"))
    if docker_engine is None:
        engine, resolved_sandbox = select_docker_engine(mode=sandbox_mode)
    else:
        engine, resolved_sandbox = docker_engine, sandbox_mode or "injected"

    if adapter_factory is None:
        # Pin-based resolution; mode controls live vs deterministic factories.
        resolved_adapter = resolve_adapter_mode(adapter_mode)
        factory: AdapterFactory | None = None
    else:
        factory = adapter_factory
        resolved_adapter = adapter_mode or "injected"

    (
        lifecycle_factory,
        sandbox,
        adapter,
        grading,
        status,
        resolved_cancellation,
    ) = build_production_lifecycle_factory(
        uow_factory=uow_factory,
        ids=ids,
        events=events,
        docker_engine=engine,
        actor=system_actor,
        auth=auth,
        adapter_factory=factory,
        adapter_mode=adapter_mode,
        cancellation=cancellation,
        object_storage=object_storage,
        event_fanout=event_fanout,
    )

    worker = WorkerRuntime(
        worker_id=worker_id,
        queue=queue,
        checkpoints=CheckpointManager(InMemoryCheckpointStore()),
        cancellation=resolved_cancellation,
        lifecycle_factory=lifecycle_factory,
        retry_policy=RetryPolicy(max_attempts=max_attempts),
        clock=SystemClock(),
        execution_timeout_seconds=execution_timeout_seconds,
    )
    return ProductionWorkerBundle(
        worker=worker,
        cancellation=resolved_cancellation,
        sandbox=sandbox,
        adapter=adapter,
        grading=grading,
        status=status,
        docker_engine=engine,
        actor=system_actor,
        sandbox_mode=resolved_sandbox,
        adapter_mode=resolved_adapter,
    )
