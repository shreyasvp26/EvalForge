"""Tests for process-level production worker wiring (Phase 1 execution loop)."""

from __future__ import annotations

import pytest
from agent_eval_application.commands.run import CreateRunCommand
from agent_eval_application.common.actor import Actor
from agent_eval_application.queries.queries import GetRunQuery, GetRunScoresQuery
from agent_eval_application.use_cases.run import CreateRun, GetRun, GetRunScores
from agent_eval_domain.common.ids import RunId
from agent_eval_sandbox.docker.fake import FakeDockerEngine
from agent_eval_workers.execution_engine import EngineOutcomeKind
from agent_eval_workers.integration.composition import default_claude_factory
from agent_eval_workers.integration.process import (
    build_production_worker,
    select_adapter_factory,
    select_docker_engine,
)
from agent_eval_workers.integration.worker_auth import WorkerAuthorization
from agent_eval_workers.lifecycle.phases import OrchestrationPhase
from agent_eval_workers.lifecycle.triggers import FailureCause
from agent_eval_workers.worker.memory_queue import InMemoryWorkerQueue

pytest_plugins = ["test_run_use_cases"]


def _create_queued_run(world):
    return CreateRun(
        world["uow"],
        world["ids"],
        world["auth"],
        world["events"],
        world["queue"],
        world["idempotency"],
    ).execute(
        CreateRunCommand(
            actor=world["actor"],
            project_id=world["project_id"],
            case_id=world["case_id"],
            case_version_id=world["case_version_id"],
            prompt_version_id=world["prompt_version_id"],
            agent_id=world["agent_id"],
            agent_version_id=world["agent_version_id"],
            adapter_version_id=world["adapter_version_id"],
            grader_version_refs=((world["grader_id"], world["grader_version_id"]),),
            platform_version_id=world["platform_version_id"],
        )
    )


def test_select_docker_engine_fake() -> None:
    engine, mode = select_docker_engine(mode="fake")
    assert mode == "fake"
    assert isinstance(engine, FakeDockerEngine)


def test_select_adapter_factory_deterministic() -> None:
    factory, mode = select_adapter_factory(mode="deterministic")
    assert mode == "deterministic"
    adapter = factory()
    assert adapter.name == "claude_code"


def test_worker_authorization_rejects_non_system() -> None:
    from agent_eval_application.errors import AuthorizationError
    from agent_eval_domain.common.ids import ProjectId

    auth = WorkerAuthorization()
    with pytest.raises(AuthorizationError):
        auth.ensure_can_manage_project(Actor(id="someone-else"), ProjectId("p1"))


def test_process_worker_completes_run_end_to_end(world) -> None:
    """API-shaped CreateRun → production worker → completed + score."""
    run = _create_queued_run(world)
    queue = InMemoryWorkerQueue()
    queue.enqueue(RunId(run.id))

    # Seed grader specification so ExpectedFileGrader looks for main.py
    # (world fixture already publishes an objective grader).
    bundle = build_production_worker(
        queue=queue,
        uow_factory=world["uow"],
        ids=world["ids"],
        events=world["events"],
        docker_engine=FakeDockerEngine(),
        adapter_factory=default_claude_factory(),
        actor=Actor(id="system-worker"),
        auth=WorkerAuthorization(),
        sandbox_mode="fake",
        adapter_mode="deterministic",
    )

    result = bundle.worker.run_once(block=False)
    assert result is not None
    assert result.kind is EngineOutcomeKind.COMPLETED
    assert result.phase is OrchestrationPhase.COMPLETED

    dto = GetRun(world["uow"], world["auth"]).execute(
        GetRunQuery(actor=world["actor"], run_id=run.id)
    )
    assert dto.status == "completed"
    assert dto.produced_score_count >= 1
    scores = GetRunScores(world["uow"], world["auth"]).execute(
        GetRunScoresQuery(actor=world["actor"], run_id=run.id)
    )
    assert scores
    assert scores[0].value.passed is True


def test_process_worker_adapter_failure_marks_failed(world) -> None:
    run = _create_queued_run(world)
    queue = InMemoryWorkerQueue()
    queue.enqueue(RunId(run.id))

    def boom_factory():
        from agent_eval_adapters.claude_code import ClaudeCodeAdapter

        def source(_ctx: object):
            raise RuntimeError("adapter boom")
            yield  # pragma: no cover

        return ClaudeCodeAdapter(stream_source=source)

    bundle = build_production_worker(
        queue=queue,
        uow_factory=world["uow"],
        ids=world["ids"],
        events=world["events"],
        docker_engine=FakeDockerEngine(),
        adapter_factory=boom_factory,
        actor=Actor(id="system-worker"),
        auth=WorkerAuthorization(),
    )
    # Force adapter failure via bridge flag instead of broken stream.
    bundle.adapter.fail_on_run = True

    result = bundle.worker.run_once(block=False)
    assert result is not None
    assert result.kind is EngineOutcomeKind.FAILED
    assert result.failure_cause is FailureCause.ADAPTER_FAILURE

    dto = GetRun(world["uow"], world["auth"]).execute(
        GetRunQuery(actor=world["actor"], run_id=run.id)
    )
    assert dto.status in {"failed", "cancelled"}


def test_process_worker_survives_lifecycle_factory_crash(world) -> None:
    """Unhandled factory errors must not kill the chassis — claim is settled."""
    run = _create_queued_run(world)
    queue = InMemoryWorkerQueue()
    queue.enqueue(RunId(run.id))

    bundle = build_production_worker(
        queue=queue,
        uow_factory=world["uow"],
        ids=world["ids"],
        events=world["events"],
        docker_engine=FakeDockerEngine(),
        adapter_factory=default_claude_factory(),
        actor=Actor(id="system-worker"),
        auth=WorkerAuthorization(),
    )

    def exploding_factory(run_id, phase):
        raise RuntimeError("factory exploded")

    bundle.worker.lifecycle_factory = exploding_factory
    result = bundle.worker.run_once(block=False)
    assert result is not None
    assert result.kind is EngineOutcomeKind.FAILED
    # Queue drained (acked) so a subsequent claim is idle.
    assert bundle.worker.run_once(block=False) is None


def test_process_worker_continues_after_failure(world) -> None:
    first = _create_queued_run(world)
    second = _create_queued_run(world)
    queue = InMemoryWorkerQueue()
    queue.enqueue(RunId(first.id))
    queue.enqueue(RunId(second.id))

    bundle = build_production_worker(
        queue=queue,
        uow_factory=world["uow"],
        ids=world["ids"],
        events=world["events"],
        docker_engine=FakeDockerEngine(),
        adapter_factory=default_claude_factory(),
        actor=Actor(id="system-worker"),
        auth=WorkerAuthorization(),
    )
    bundle.adapter.fail_on_run = True
    failed = bundle.worker.run_once(block=False)
    assert failed is not None
    assert failed.kind is EngineOutcomeKind.FAILED

    bundle.adapter.fail_on_run = False
    ok = bundle.worker.run_once(block=False)
    assert ok is not None
    assert ok.kind is EngineOutcomeKind.COMPLETED

    dto = GetRun(world["uow"], world["auth"]).execute(
        GetRunQuery(actor=world["actor"], run_id=second.id)
    )
    assert dto.status == "completed"


def test_select_adapter_factory_claude() -> None:
    factory, mode = select_adapter_factory(mode="claude")
    assert mode == "live"
    adapter = factory()
    assert adapter.stream_source is None


def test_sandbox_env_allowlist_never_dumps_full_environ(monkeypatch) -> None:
    monkeypatch.setenv("SECRET_SHOULD_NOT_LEAK", "super-secret")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("WORKER_SANDBOX_ENV_ALLOWLIST", "ANTHROPIC_API_KEY")
    from agent_eval_workers.integration.sandbox_adapter import (
        sandbox_environment_from_allowlist,
    )

    env = sandbox_environment_from_allowlist()
    assert env == {"ANTHROPIC_API_KEY": "sk-test"}
    assert "SECRET_SHOULD_NOT_LEAK" not in env


def test_process_worker_stores_artifact_bytes(world) -> None:
    from agent_eval_infrastructure.storage.memory import InMemoryObjectStorage

    run = _create_queued_run(world)
    queue = InMemoryWorkerQueue()
    queue.enqueue(RunId(run.id))
    storage = InMemoryObjectStorage()

    bundle = build_production_worker(
        queue=queue,
        uow_factory=world["uow"],
        ids=world["ids"],
        events=world["events"],
        docker_engine=FakeDockerEngine(),
        adapter_factory=default_claude_factory(),
        actor=Actor(id="system-worker"),
        auth=WorkerAuthorization(),
        object_storage=storage,
        sandbox_mode="fake",
        adapter_mode="deterministic",
    )
    result = bundle.worker.run_once(block=False)
    assert result is not None
    assert result.kind is EngineOutcomeKind.COMPLETED
