"""Optional live-Docker production worker integration tests."""

from __future__ import annotations

import shutil

import docker
import pytest
from agent_eval_application.commands.case import (
    CreateCaseDraftVersionCommand,
    PublishCaseVersionCommand,
)
from agent_eval_application.commands.run import CreateRunCommand
from agent_eval_application.queries.queries import GetRunQuery, GetRunScoresQuery
from agent_eval_application.use_cases.case import (
    CreateCaseDraftVersion,
    PublishCaseVersion,
)
from agent_eval_application.use_cases.run import CreateRun, GetRun, GetRunScores
from agent_eval_domain.common.ids import RunId
from agent_eval_infrastructure.storage.memory import InMemoryObjectStorage
from agent_eval_sandbox.docker.engine import DockerPyEngine
from agent_eval_workers.execution_engine.results import EngineOutcomeKind
from agent_eval_workers.integration.process import build_production_worker
from agent_eval_workers.worker.memory_queue import InMemoryWorkerQueue

pytest_plugins = ["test_run_use_cases"]
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        __import__("os").environ.get("EVALFORGE_LIVE_WORKER_DOCKER", "0") != "1",
        reason=(
            "Set EVALFORGE_LIVE_WORKER_DOCKER=1 for full worker+Docker e2e "
            "(Compose + sandbox/tests cover the same path)."
        ),
    ),
]

# Tiny public repository used to prove exact-SHA materialization in Docker.
_PUBLIC_REPO = "https://github.com/octocat/Hello-World.git"
_PUBLIC_SHA = "7fd1a60b01f91b314f59955a4e4d4e80d8edf11d"


def _docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        client = docker.from_env()
        client.ping()
        return True
    except Exception:  # noqa: BLE001
        return False


@pytest.fixture(scope="module")
def live_engine() -> DockerPyEngine:
    if not _docker_available():
        pytest.skip("Docker daemon not available")
    engine = DockerPyEngine.from_env()
    images = {tag for img in engine.client.images.list() for tag in img.tags}
    if "evalforge/sandbox:local" not in images:
        pytest.skip(
            "evalforge/sandbox:local image required for git materialization "
            "(busybox has no git). Build via Compose sandbox-image service."
        )
    return engine


def test_production_worker_real_docker_deterministic(
    world, live_engine: DockerPyEngine, monkeypatch
) -> None:
    """CreateRun → real Docker sandbox → git checkout SHA → grade → COMPLETED."""
    monkeypatch.setenv("WORKER_SANDBOX_IMAGE", "evalforge/sandbox:local")
    # bridge: repository fetch requires egress; none would block materialization.
    monkeypatch.setenv("WORKER_SANDBOX_NETWORK", "bridge")
    monkeypatch.setenv("WORKER_SANDBOX_ENV_ALLOWLIST", "PATH,HOME,TERM")
    monkeypatch.setenv("WORKER_SANDBOX_VERIFY", "0")

    # Replace fixture example.com URL with a real public repo + exact SHA.
    draft = CreateCaseDraftVersion(
        world["uow"], world["ids"], world["auth"], world["events"]
    ).execute(
        CreateCaseDraftVersionCommand(
            actor=world["actor"],
            case_id=world["case_id"],
            description="Phase 4 Docker materialization",
            repository_url=_PUBLIC_REPO,
            commit_sha=_PUBLIC_SHA,
            expected_checks=("pytest",),
            applicable_grader_ids=(world["grader_id"],),
            prompt_version_id=world["prompt_version_id"],
        )
    )
    case_version = PublishCaseVersion(
        world["uow"], world["auth"], world["events"]
    ).execute(
        PublishCaseVersionCommand(
            actor=world["actor"],
            case_id=world["case_id"],
            version_id=draft.id,
        )
    )

    storage = InMemoryObjectStorage()
    queue = InMemoryWorkerQueue()
    bundle = build_production_worker(
        queue=queue,
        uow_factory=world["uow"],
        ids=world["ids"],
        events=world["events"],
        docker_engine=live_engine,
        sandbox_mode="docker",
        adapter_mode="deterministic",
        actor=world["actor"],
        auth=world["auth"],
        object_storage=storage,
        max_attempts=1,
    )

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
            case_version_id=case_version.id,
            prompt_version_id=world["prompt_version_id"],
            agent_id=world["agent_id"],
            agent_version_id=world["agent_version_id"],
            adapter_version_id=world["adapter_version_id"],
            grader_version_refs=((world["grader_id"], world["grader_version_id"]),),
            platform_version_id=world["platform_version_id"],
        )
    )
    queue.enqueue(RunId(run.id))
    result = bundle.worker.run_once(block=False)
    assert result is not None, "worker returned no result"
    if result.kind is not EngineOutcomeKind.COMPLETED:
        final = GetRun(world["uow"], world["auth"]).execute(
            GetRunQuery(actor=world["actor"], run_id=run.id)
        )
        raise AssertionError(
            f"expected COMPLETED, got {result.kind} cause={result.failure_cause} "
            f"phase={result.phase} status={final.status} "
            f"failure_reason={final.failure_reason!r} "
            f"provisioned={bundle.sandbox.provisioned} "
            f"destroyed={bundle.sandbox.destroyed}"
        )

    final = GetRun(world["uow"], world["auth"]).execute(
        GetRunQuery(actor=world["actor"], run_id=run.id)
    )
    assert final.status == "completed"
    scores = GetRunScores(world["uow"], world["auth"]).execute(
        GetRunScoresQuery(actor=world["actor"], run_id=run.id)
    )
    assert scores
    assert any(s.value.passed for s in scores)
    assert RunId(run.id) in bundle.sandbox.destroyed
    assert RunId(run.id) in bundle.sandbox.provisioned
