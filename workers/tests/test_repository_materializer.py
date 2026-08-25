"""Tests for repository materialization at pinned revisions."""

from __future__ import annotations

import pytest
from agent_eval_application.common.actor import Actor
from agent_eval_application.use_cases.case import ListCasesByProject
from agent_eval_application.use_cases.run import GetRun
from agent_eval_domain.common.ids import RunId
from agent_eval_sandbox.docker.fake import FakeDockerEngine
from agent_eval_sandbox.docker.sandbox import DockerSandbox
from agent_eval_sandbox.manager import SandboxManager
from agent_eval_sandbox.models import SandboxSpec
from agent_eval_workers.execution_engine import EngineOutcomeKind
from agent_eval_workers.integration.process import build_production_worker
from agent_eval_workers.integration.repository_materializer import (
    CaseReferenceResolver,
    ReferenceRepository,
    RepositoryMaterializationError,
    RepositoryMaterializer,
)
from agent_eval_workers.integration.worker_auth import WorkerAuthorization
from agent_eval_workers.lifecycle.triggers import FailureCause
from agent_eval_workers.worker.memory_queue import InMemoryWorkerQueue

pytest_plugins = ["test_run_use_cases"]


def test_case_reference_resolver_loads_pinned_repo(world) -> None:
    from agent_eval_application.commands.run import CreateRunCommand
    from agent_eval_application.use_cases.run import CreateRun

    run = CreateRun(
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
            platform_version_id="platform-v1",
        )
    )
    resolver = CaseReferenceResolver(
        actor=world["actor"],
        get_run=GetRun(world["uow"], world["auth"]),
        list_cases=ListCasesByProject(world["uow"], world["auth"]),
    )
    ref = resolver.resolve(RunId(run.id))
    assert ref.repository_url == "https://example.com/r.git"
    assert ref.commit_sha == "deadbeef"


def test_materializer_checks_out_exact_sha() -> None:
    engine = FakeDockerEngine()
    manager = SandboxManager(runtime=DockerSandbox(engine=engine))
    handle = manager.create(SandboxSpec(image="busybox:1.36", working_dir="/workspace"))
    handle = manager.start(handle)
    materializer = RepositoryMaterializer(manager=manager)
    workspace = materializer.materialize(
        handle,
        ReferenceRepository(
            repository_url="https://example.com/r.git",
            commit_sha="abc1234",
        ),
    )
    assert workspace == "/workspace"
    assert engine.checked_out_sha == "abc1234"
    container = next(iter(engine.containers.values()))
    assert any("fetch" in " ".join(cmd) for cmd in container.exec_log)


def test_materializer_rejects_head_mismatch() -> None:
    engine = FakeDockerEngine()
    manager = SandboxManager(runtime=DockerSandbox(engine=engine))
    handle = manager.create(SandboxSpec(image="busybox:1.36", working_dir="/workspace"))
    handle = manager.start(handle)

    # Force rev-parse to return a different SHA than checkout.
    original = engine._maybe_handle_git

    def mismatched(container_id: str, command: list[str]):
        if "rev-parse" in command:
            return 0, b"ffffffff\n", b"", False
        return original(container_id, command)

    engine._maybe_handle_git = mismatched  # type: ignore[method-assign]
    materializer = RepositoryMaterializer(manager=manager)
    with pytest.raises(RepositoryMaterializationError, match="does not match"):
        materializer.materialize(
            handle,
            ReferenceRepository(
                repository_url="https://example.com/r.git",
                commit_sha="abc1234",
            ),
        )


def test_process_worker_fails_when_git_fails(world) -> None:
    from agent_eval_application.commands.run import CreateRunCommand
    from agent_eval_application.queries.queries import GetRunQuery
    from agent_eval_application.use_cases.run import CreateRun, GetRun

    run = CreateRun(
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
            platform_version_id="platform-v1",
        )
    )
    queue = InMemoryWorkerQueue()
    queue.enqueue(RunId(run.id))
    engine = FakeDockerEngine(fail_git=True)
    bundle = build_production_worker(
        queue=queue,
        uow_factory=world["uow"],
        ids=world["ids"],
        events=world["events"],
        docker_engine=engine,
        actor=Actor(id="system-worker"),
        auth=WorkerAuthorization(),
        sandbox_mode="fake",
        adapter_mode="deterministic",
        max_attempts=1,
    )
    result = bundle.worker.run_once(block=False)
    assert result is not None
    assert result.failure_cause is FailureCause.SANDBOX_FAILURE
    dto = GetRun(world["uow"], world["auth"]).execute(
        GetRunQuery(actor=world["actor"], run_id=run.id)
    )
    # Exhausted sandbox retries project a terminal outcome (failed or cancelled
    # depending on worker ack path); materialization must not leave the run queued.
    assert dto.status in {"failed", "cancelled"}
    if dto.status == "failed":
        assert dto.failure_reason
        assert (
            "Repository" in dto.failure_reason
            or "git" in dto.failure_reason.lower()
            or "materializ" in dto.failure_reason.lower()
        )


def test_process_worker_materializes_before_adapter(world) -> None:
    from agent_eval_application.commands.run import CreateRunCommand
    from agent_eval_application.use_cases.run import CreateRun

    run = CreateRun(
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
            platform_version_id="platform-v1",
        )
    )
    queue = InMemoryWorkerQueue()
    queue.enqueue(RunId(run.id))
    engine = FakeDockerEngine()
    bundle = build_production_worker(
        queue=queue,
        uow_factory=world["uow"],
        ids=world["ids"],
        events=world["events"],
        docker_engine=engine,
        actor=Actor(id="system-worker"),
        auth=WorkerAuthorization(),
        sandbox_mode="fake",
        adapter_mode="deterministic",
    )
    result = bundle.worker.run_once(block=False)
    assert result is not None
    assert result.kind is EngineOutcomeKind.COMPLETED
    assert engine.checked_out_sha == "deadbeef"
    # Deterministic adapter wrote main.py into the materialized workspace; the
    # workspace probe + ExpectedFile grader both validated that result.
    from agent_eval_application.queries.queries import GetRunScoresQuery
    from agent_eval_application.use_cases.run import GetRunScores

    scores = GetRunScores(world["uow"], world["auth"]).execute(
        GetRunScoresQuery(actor=world["actor"], run_id=run.id)
    )
    assert len(scores) >= 1
    assert scores[0].value.passed is True
