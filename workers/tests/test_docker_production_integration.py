"""Optional live-Docker production worker integration tests."""

from __future__ import annotations

import shutil

import docker
import pytest
from agent_eval_application.commands.run import CreateRunCommand
from agent_eval_application.queries.queries import GetRunQuery, GetRunScoresQuery
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
    # Prefer the Compose sandbox image when present; else busybox for CI/local.
    images = {tag for img in engine.client.images.list() for tag in img.tags}
    if "evalforge/sandbox:local" not in images:
        engine.client.images.pull("busybox:1.36")
    return engine


def test_production_worker_real_docker_deterministic(
    world, live_engine: DockerPyEngine, monkeypatch
) -> None:
    """API-shaped CreateRun → worker → real DockerSandbox → grade → COMPLETED."""
    monkeypatch.setenv(
        "WORKER_SANDBOX_IMAGE",
        (
            "evalforge/sandbox:local"
            if any(
                "evalforge/sandbox:local" in (img.tags or [])
                for img in live_engine.client.images.list()
            )
            else "busybox:1.36"
        ),
    )
    monkeypatch.setenv("WORKER_SANDBOX_NETWORK", "none")
    monkeypatch.setenv("WORKER_SANDBOX_ENV_ALLOWLIST", "PATH,HOME,TERM")
    # Live Docker exec can be slow under Desktop load; skip verify in this test —
    # sandbox integration suite already covers create/exec/timeout/cleanup.
    monkeypatch.setenv("WORKER_SANDBOX_VERIFY", "0")

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
            case_version_id=world["case_version_id"],
            prompt_version_id=world["prompt_version_id"],
            agent_id=world["agent_id"],
            agent_version_id=world["agent_version_id"],
            adapter_version_id=world["adapter_version_id"],
            grader_version_refs=((world["grader_id"], world["grader_version_id"]),),
            platform_version_id="platform-1.0.0",
        )
    )
    queue.enqueue(RunId(run.id))
    result = bundle.worker.run_once(block=False)
    assert result is not None, "worker returned no result"
    if result.kind is not EngineOutcomeKind.COMPLETED:
        # Surface sandbox/adapter diagnostics for live Docker failures.
        raise AssertionError(
            f"expected COMPLETED, got {result.kind} cause={result.failure_cause} "
            f"phase={result.phase} provisioned={bundle.sandbox.provisioned} "
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
    # Sandbox was destroyed after completion.
    assert RunId(run.id) in bundle.sandbox.destroyed
    assert RunId(run.id) in bundle.sandbox.provisioned
