"""Production composition root — real Sandbox / Adapter / Graders / Application.

Engine remains Docker-unaware. Workers remain Claude-unaware (factory only).
Graders stay isolated via the Grader SDK. Mock only JudgeProvider in tests.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass, field

from agent_eval_adapters.claude_code import ClaudeCodeAdapter
from agent_eval_adapters.sdk.adapter import Adapter
from agent_eval_adapters.sdk.models import RunMetadata
from agent_eval_application.common.actor import Actor
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
from agent_eval_graders.objective import DiffValidationGrader, ExpectedFileGrader
from agent_eval_graders.rubric import (
    MockJudgeProvider,
    RubricCriterion,
    RubricGrader,
    RubricSpecification,
)
from agent_eval_sandbox.docker.sandbox import DockerSandbox
from agent_eval_sandbox.manager import SandboxManager
from agent_eval_sandbox.ports import DockerEngine

from agent_eval_workers.cancellation.registry import InMemoryCancellationRegistry
from agent_eval_workers.checkpoints.manager import CheckpointManager
from agent_eval_workers.checkpoints.memory import InMemoryCheckpointStore
from agent_eval_workers.clock import FakeClock, SystemClock
from agent_eval_workers.event_pipeline.pipeline import (
    EventPersistencePipeline,
    UseCaseEventWriter,
)
from agent_eval_workers.event_pipeline.projector import ProjectionHub
from agent_eval_workers.execution_engine.lifecycle_driver import LifecycleDriver
from agent_eval_workers.integration.adapter_bridge import SdkAdapterBridge
from agent_eval_workers.integration.grading_scheduler import (
    GraderInvocationSpec,
    GraderSdkScheduler,
)
from agent_eval_workers.integration.registry import RunSandboxRegistry
from agent_eval_workers.integration.run_status import ApplicationRunStatus
from agent_eval_workers.integration.sandbox_adapter import ManagedSandboxAdapter
from agent_eval_workers.lifecycle.machine import RunLifecycle
from agent_eval_workers.lifecycle.orchestrator import LifecycleOrchestrator
from agent_eval_workers.lifecycle.phases import OrchestrationPhase
from agent_eval_workers.worker.memory_queue import InMemoryWorkerQueue
from agent_eval_workers.worker.retry import RetryPolicy
from agent_eval_workers.worker.runtime import WorkerRuntime

StreamSource = Callable[[object], Iterator[str]]
AdapterFactory = Callable[[], Adapter]


@dataclass(slots=True)
class ProductionHarness:
    """Fully wired production execution pipeline for integration tests."""

    queue: InMemoryWorkerQueue
    checkpoints: CheckpointManager
    cancellation: InMemoryCancellationRegistry
    pipeline: EventPersistencePipeline
    sandbox: ManagedSandboxAdapter
    adapter: SdkAdapterBridge
    grading: GraderSdkScheduler
    status: ApplicationRunStatus
    worker: WorkerRuntime
    sandbox_registry: RunSandboxRegistry
    docker_engine: DockerEngine
    actor: Actor
    projections: ProjectionHub = field(default_factory=ProjectionHub)
    clock: FakeClock | SystemClock = field(default_factory=SystemClock)

    def enqueue(self, run_id: str) -> None:
        self.queue.enqueue(RunId(run_id))


def _default_claude_stream() -> Iterator[str]:
    import json

    yield json.dumps(
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": "toolu_1",
                        "name": "Bash",
                        "input": {"command": "pytest -q"},
                    }
                ],
            },
        }
    )
    yield json.dumps(
        {
            "type": "user",
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "toolu_1",
                        "content": "1 passed",
                    }
                ],
            },
        }
    )
    yield json.dumps(
        {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "id": "toolu_2",
                        "name": "Edit",
                        "input": {
                            "file_path": "main.py",
                            "old_string": "x",
                            "new_string": "y",
                        },
                    }
                ],
            },
        }
    )
    yield json.dumps(
        {
            "type": "result",
            "subtype": "success",
            "is_error": False,
            "result": "done",
        }
    )


def _write_deterministic_workspace(context: object) -> None:
    """Materialize the synthetic edit into the sandbox working directory.

    Deterministic mode still injects NDJSON, but also writes the files the
    stream claims to edit so graders can verify the same workspace.
    """
    from agent_eval_adapters.sdk.context import ExecutionContext
    from agent_eval_sandbox.models import ExecutionRequest

    if not isinstance(context, ExecutionContext):
        return
    workspace = context.working_directory.rstrip("/")
    # Keep content tiny and deterministic; path matches ExpectedFile default.
    script = (
        f"mkdir -p {workspace} && "
        f"printf '%s\\n' 'print(\"evalforge-deterministic\")' > {workspace}/main.py"
    )
    context.sandbox_exec.execute(
        context.sandbox,
        ExecutionRequest(
            command=("sh", "-c", script),
            working_dir=workspace,
            timeout_seconds=30.0,
        ),
    )


def default_claude_factory(
    *,
    stream_lines: Sequence[str] | None = None,
) -> AdapterFactory:
    """Composition-time Claude Code registration — Engine never imports this."""

    lines = list(stream_lines) if stream_lines is not None else None

    def factory() -> Adapter:
        def source(ctx: object) -> Iterator[str]:
            _write_deterministic_workspace(ctx)
            if lines is not None:
                yield from lines
            else:
                yield from _default_claude_stream()

        return ClaudeCodeAdapter(stream_source=source)

    return factory


def build_production_harness(
    *,
    docker_engine: DockerEngine,
    uow_factory: object,
    ids: object,
    auth: object,
    events: object,
    actor: Actor | None = None,
    grader_specs: Sequence[GraderInvocationSpec] | None = None,
    adapter_factory: AdapterFactory | None = None,
    run_metadata_factory: Callable[[RunId], RunMetadata] | None = None,
    fail_sandbox: bool = False,
    fail_adapter: bool = False,
    worker_id: str = "worker-prod-1",
    max_attempts: int = 3,
    execution_timeout_seconds: float | None = None,
    clock: FakeClock | None = None,
    batch_size: int = 1,
    judge_response: str | None = None,
) -> ProductionHarness:
    """Wire Worker → Engine → Docker Sandbox → Claude Adapter → Graders → App."""
    system_actor = actor or Actor(id="system-worker")
    sandbox_registry = RunSandboxRegistry()
    manager = SandboxManager(runtime=DockerSandbox(engine=docker_engine))
    sandbox = ManagedSandboxAdapter(
        manager=manager,
        registry=sandbox_registry,
        fail_on_provision=fail_sandbox,
    )

    writer = UseCaseEventWriter(
        record_event_uc=RecordExecutionEvent(uow_factory, auth, events),
        record_artifact_uc=RecordArtifact(uow_factory, ids, auth, events),
    )
    projections = ProjectionHub()
    pipeline = EventPersistencePipeline(
        writer=writer,
        actor=system_actor,
        projections=projections,
        batch_size=batch_size,
    )

    cancellation = InMemoryCancellationRegistry()
    factory = adapter_factory or default_claude_factory()
    adapter = SdkAdapterBridge(
        stream=pipeline,
        sandboxes=sandbox_registry,
        manager=manager,
        adapter_factory=factory,
        cancellation=cancellation,
        run_metadata_factory=run_metadata_factory
        or (
            lambda rid: RunMetadata(
                run_id=rid.value,
                agent_version_id="agent-v1",
                adapter_version_id="adapter-v1",
                prompt_version_id="prompt-v1",
                case_version_id="case-v1",
            )
        ),
        fail_on_run=fail_adapter,
    )

    if grader_specs is None:
        rubric = RubricSpecification(
            title="Quality",
            instructions="Score the agent's changes for correctness.",
            criteria=(RubricCriterion(id="correctness", description="Does it work?"),),
            pass_threshold=0.5,
        )
        judge_body = judge_response or (
            '{"numeric": 0.9, "passed": true, "reason": "Looks good",'
            ' "criteria": [{"criterion_id": "correctness", "score": 0.9,'
            ' "reason": "ok", "passed": true}]}'
        )

        def make_files() -> ExpectedFileGrader:
            return ExpectedFileGrader(expected_paths=("main.py",))

        def make_diff() -> DiffValidationGrader:
            return DiffValidationGrader()

        def make_rubric() -> RubricGrader:
            return RubricGrader(
                rubric=rubric,
                provider=MockJudgeProvider(response=judge_body),
            )

        grader_specs = (
            GraderInvocationSpec(
                name="expected_file",
                grader_id="grader-files",
                grader_version_id="gv-files",
                factory=make_files,
                specification="main.py",
            ),
            GraderInvocationSpec(
                name="diff_validation",
                grader_id="grader-diff",
                grader_version_id="gv-diff",
                factory=make_diff,
                specification="diff",
            ),
            GraderInvocationSpec(
                name="rubric",
                grader_id="grader-rubric",
                grader_version_id="gv-rubric",
                factory=make_rubric,
                specification=rubric.instructions,
            ),
        )

    grading = GraderSdkScheduler(
        actor=system_actor,
        get_run=GetRun(uow_factory, auth),
        get_events=GetRunEvents(uow_factory, auth),
        get_artifacts=GetRunArtifacts(uow_factory, auth),
        record_score=RecordScore(uow_factory, ids, auth, events),
        graders=tuple(grader_specs),
    )

    status = ApplicationRunStatus(
        actor=system_actor,
        sandbox_registry=sandbox_registry,
        start_run=StartRun(uow_factory, auth, events),
        start_grading=StartGrading(uow_factory, auth, events),
        complete_run=CompleteRun(uow_factory, auth, events),
        fail_run=FailRun(uow_factory, auth, events),
        cancel_run=CancelRun(uow_factory, auth, events),
    )

    store = InMemoryCheckpointStore()
    checkpoints = CheckpointManager(store)
    queue = InMemoryWorkerQueue()
    clock_impl: FakeClock | SystemClock = clock if clock is not None else SystemClock()

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
    return ProductionHarness(
        queue=queue,
        checkpoints=checkpoints,
        cancellation=cancellation,
        pipeline=pipeline,
        sandbox=sandbox,
        adapter=adapter,
        grading=grading,
        status=status,
        worker=worker,
        sandbox_registry=sandbox_registry,
        docker_engine=docker_engine,
        actor=system_actor,
        projections=projections,
        clock=clock_impl,
    )


def rebuild_production_worker(
    harness: ProductionHarness,
    *,
    worker_id: str = "worker-prod-2",
) -> WorkerRuntime:
    """Simulate Worker restart against the same durable checkpoints / queue."""

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
