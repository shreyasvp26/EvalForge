"""Live Gemini Docker integration tests for Phase 5 evaluation."""

from __future__ import annotations

import os
import shutil

import docker
import pytest
from agent_eval_application.commands.agent import (
    CreateAdapterCommand,
    CreateAdapterDraftVersionCommand,
    CreateAgentCommand,
    CreateAgentDraftVersionCommand,
    PublishAdapterVersionCommand,
    PublishAgentVersionCommand,
)
from agent_eval_application.commands.case import (
    CreateCaseDraftVersionCommand,
    CreatePromptDraftVersionCommand,
    PublishCaseVersionCommand,
    PublishPromptVersionCommand,
)
from agent_eval_application.commands.grader import (
    CreateGraderDraftVersionCommand,
    PublishGraderVersionCommand,
)
from agent_eval_application.commands.run import CreateRunCommand
from agent_eval_application.queries.queries import (
    GetRunEventsQuery,
    GetRunQuery,
    GetRunScoresQuery,
)
from agent_eval_application.use_cases.agent import (
    CreateAdapter,
    CreateAdapterDraftVersion,
    CreateAgent,
    CreateAgentDraftVersion,
    PublishAdapterVersion,
    PublishAgentVersion,
)
from agent_eval_application.use_cases.case import (
    CreateCaseDraftVersion,
    CreatePromptDraftVersion,
    PublishCaseVersion,
    PublishPromptVersion,
)
from agent_eval_application.use_cases.grader import (
    CreateGraderDraftVersion,
    PublishGraderVersion,
)
from agent_eval_application.use_cases.run import (
    CreateRun,
    GetRun,
    GetRunEvents,
    GetRunScores,
)
from agent_eval_domain.common.ids import RunId
from agent_eval_infrastructure.storage.memory import InMemoryObjectStorage
from agent_eval_sandbox.docker.engine import DockerPyEngine
from agent_eval_workers.execution_engine.results import EngineOutcomeKind
from agent_eval_workers.integration.canonical_evaluation import (
    CANONICAL_CALCULATOR_BROKEN_SHA,
    CANONICAL_CALCULATOR_PROMPT,
    CANONICAL_CALCULATOR_REPO,
)
from agent_eval_workers.integration.process import build_production_worker
from agent_eval_workers.worker.memory_queue import InMemoryWorkerQueue

pytest_plugins = ["test_run_use_cases"]
pytestmark = [
    pytest.mark.integration,
    pytest.mark.gemini_live,
    pytest.mark.skipif(
        os.environ.get("EVALFORGE_LIVE_GEMINI_DOCKER", "0") != "1",
        reason="Set EVALFORGE_LIVE_GEMINI_DOCKER=1 for live Gemini Docker e2e",
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


def _gemini_credentials_available() -> bool:
    return bool(
        os.environ.get("GEMINI_API_KEY", "").strip()
        or os.environ.get("GOOGLE_API_KEY", "").strip()
    )


def _sandbox_image_ready(engine: DockerPyEngine) -> bool:
    images = {tag for img in engine.client.images.list() for tag in img.tags}
    return "evalforge/sandbox:local" in images


@pytest.fixture(scope="module")
def live_engine() -> DockerPyEngine:
    if not _docker_available():
        pytest.skip("Docker daemon not available")
    engine = DockerPyEngine.from_env()
    if not _sandbox_image_ready(engine):
        pytest.skip(
            "evalforge/sandbox:local image required "
            "(build with EVALFORGE_INSTALL_GEMINI_CLI=1)"
        )
    return engine


def _build_gemini_world(world, *, prompt: str = CANONICAL_CALCULATOR_PROMPT):
    actor = world["actor"]
    uow, ids, auth, events = (
        world["uow"],
        world["ids"],
        world["auth"],
        world["events"],
    )

    test_grader = CreateGraderDraftVersion(uow, ids, auth, events).execute(
        CreateGraderDraftVersionCommand(
            actor=actor,
            grader_id=world["grader_id"],
            label="workspace-pytest",
            specification="workspace:python3 -m pytest tests/ -q",
        )
    )
    test_grader = PublishGraderVersion(uow, auth, events).execute(
        PublishGraderVersionCommand(
            actor=actor,
            grader_id=world["grader_id"],
            version_id=test_grader.id,
        )
    )

    prompt_version = CreatePromptDraftVersion(uow, ids, auth, events).execute(
        CreatePromptDraftVersionCommand(
            actor=actor,
            case_id=world["case_id"],
            content=prompt,
        )
    )
    PublishPromptVersion(uow, auth, events).execute(
        PublishPromptVersionCommand(
            actor=actor,
            case_id=world["case_id"],
            version_id=prompt_version.id,
        )
    )

    case_version = CreateCaseDraftVersion(uow, ids, auth, events).execute(
        CreateCaseDraftVersionCommand(
            actor=actor,
            case_id=world["case_id"],
            description="Phase 5 live Gemini calculator evaluation",
            repository_url=CANONICAL_CALCULATOR_REPO,
            commit_sha=CANONICAL_CALCULATOR_BROKEN_SHA,
            expected_checks=("pytest",),
            applicable_grader_ids=(world["grader_id"],),
            prompt_version_id=prompt_version.id,
        )
    )
    case_version = PublishCaseVersion(uow, auth, events).execute(
        PublishCaseVersionCommand(
            actor=actor,
            case_id=world["case_id"],
            version_id=case_version.id,
        )
    )

    agent = CreateAgent(uow, ids, auth, events).execute(
        CreateAgentCommand(actor=actor, name="Gemini Agent")
    )
    agent_version = CreateAgentDraftVersion(uow, ids, auth, events).execute(
        CreateAgentDraftVersionCommand(actor=actor, agent_id=agent.id, label="1.0")
    )
    agent_version = PublishAgentVersion(uow, auth, events).execute(
        PublishAgentVersionCommand(
            actor=actor, agent_id=agent.id, version_id=agent_version.id
        )
    )

    adapter = CreateAdapter(uow, ids, auth, events).execute(
        CreateAdapterCommand(actor=actor, agent_id=agent.id, name="gemini_cli")
    )
    adapter_version = CreateAdapterDraftVersion(uow, ids, auth, events).execute(
        CreateAdapterDraftVersionCommand(
            actor=actor, adapter_id=adapter.id, label="1.0"
        )
    )
    adapter_version = PublishAdapterVersion(uow, auth, events).execute(
        PublishAdapterVersionCommand(
            actor=actor, adapter_id=adapter.id, version_id=adapter_version.id
        )
    )

    world = dict(world)
    world["case_version_id"] = case_version.id
    world["prompt_version_id"] = prompt_version.id
    world["agent_id"] = agent.id
    world["agent_version_id"] = agent_version.id
    world["adapter_version_id"] = adapter_version.id
    world["grader_version_id"] = test_grader.id
    return world


def test_live_gemini_missing_api_key_fails_fast(
    world, live_engine: DockerPyEngine, monkeypatch
) -> None:
    gemini_world = _build_gemini_world(world)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setenv("WORKER_SANDBOX_IMAGE", "evalforge/sandbox:local")
    monkeypatch.setenv("WORKER_SANDBOX_NETWORK", "bridge")
    monkeypatch.setenv(
        "WORKER_SANDBOX_ENV_ALLOWLIST",
        "GEMINI_API_KEY,GOOGLE_API_KEY,PATH,HOME,TERM",
    )

    storage = InMemoryObjectStorage()
    queue = InMemoryWorkerQueue()
    bundle = build_production_worker(
        queue=queue,
        uow_factory=gemini_world["uow"],
        ids=gemini_world["ids"],
        events=gemini_world["events"],
        docker_engine=live_engine,
        sandbox_mode="docker",
        adapter_mode="live",
        actor=gemini_world["actor"],
        auth=gemini_world["auth"],
        object_storage=storage,
        max_attempts=1,
    )

    run = CreateRun(
        gemini_world["uow"],
        gemini_world["ids"],
        gemini_world["auth"],
        gemini_world["events"],
        gemini_world["queue"],
        gemini_world["idempotency"],
    ).execute(
        CreateRunCommand(
            actor=gemini_world["actor"],
            project_id=gemini_world["project_id"],
            case_id=gemini_world["case_id"],
            case_version_id=gemini_world["case_version_id"],
            prompt_version_id=gemini_world["prompt_version_id"],
            agent_id=gemini_world["agent_id"],
            agent_version_id=gemini_world["agent_version_id"],
            adapter_version_id=gemini_world["adapter_version_id"],
            grader_version_refs=(
                (gemini_world["grader_id"], gemini_world["grader_version_id"]),
            ),
            platform_version_id="platform-gemini-live",
        )
    )
    queue.enqueue(RunId(run.id))
    result = bundle.worker.run_once(block=False)
    assert result is not None
    assert result.kind is not EngineOutcomeKind.COMPLETED
    final = GetRun(gemini_world["uow"], gemini_world["auth"]).execute(
        GetRunQuery(actor=gemini_world["actor"], run_id=run.id)
    )
    assert final.failure_reason
    assert "GEMINI_API_KEY" in final.failure_reason


@pytest.mark.skipif(
    not _gemini_credentials_available(),
    reason="GEMINI_API_KEY or GOOGLE_API_KEY required for live Gemini proof",
)
def test_live_gemini_docker_calculator_evaluation(
    world, live_engine: DockerPyEngine, monkeypatch
) -> None:
    """CreateRun → Docker → materialize repo @ SHA → Gemini CLI → grade → COMPLETED."""
    gemini_world = _build_gemini_world(world)
    monkeypatch.setenv("WORKER_SANDBOX_IMAGE", "evalforge/sandbox:local")
    monkeypatch.setenv("WORKER_SANDBOX_NETWORK", "bridge")
    monkeypatch.setenv(
        "WORKER_SANDBOX_ENV_ALLOWLIST",
        "GEMINI_API_KEY,GOOGLE_API_KEY,PATH,HOME,TERM",
    )
    monkeypatch.setenv("WORKER_SANDBOX_VERIFY", "0")

    storage = InMemoryObjectStorage()
    queue = InMemoryWorkerQueue()
    bundle = build_production_worker(
        queue=queue,
        uow_factory=gemini_world["uow"],
        ids=gemini_world["ids"],
        events=gemini_world["events"],
        docker_engine=live_engine,
        sandbox_mode="docker",
        adapter_mode="live",
        actor=gemini_world["actor"],
        auth=gemini_world["auth"],
        object_storage=storage,
        max_attempts=1,
        execution_timeout_seconds=600.0,
    )

    run = CreateRun(
        gemini_world["uow"],
        gemini_world["ids"],
        gemini_world["auth"],
        gemini_world["events"],
        gemini_world["queue"],
        gemini_world["idempotency"],
    ).execute(
        CreateRunCommand(
            actor=gemini_world["actor"],
            project_id=gemini_world["project_id"],
            case_id=gemini_world["case_id"],
            case_version_id=gemini_world["case_version_id"],
            prompt_version_id=gemini_world["prompt_version_id"],
            agent_id=gemini_world["agent_id"],
            agent_version_id=gemini_world["agent_version_id"],
            adapter_version_id=gemini_world["adapter_version_id"],
            grader_version_refs=(
                (gemini_world["grader_id"], gemini_world["grader_version_id"]),
            ),
            platform_version_id="platform-gemini-live",
        )
    )
    queue.enqueue(RunId(run.id))
    result = bundle.worker.run_once(block=False)
    assert result is not None, "worker returned no result"

    final = GetRun(gemini_world["uow"], gemini_world["auth"]).execute(
        GetRunQuery(actor=gemini_world["actor"], run_id=run.id)
    )
    scores = GetRunScores(gemini_world["uow"], gemini_world["auth"]).execute(
        GetRunScoresQuery(actor=gemini_world["actor"], run_id=run.id)
    )
    events = GetRunEvents(gemini_world["uow"], gemini_world["auth"]).execute(
        GetRunEventsQuery(actor=gemini_world["actor"], run_id=run.id)
    )

    if result.kind is not EngineOutcomeKind.COMPLETED:
        raise AssertionError(
            f"expected COMPLETED, got {result.kind} cause={result.failure_cause} "
            f"phase={result.phase} status={final.status} "
            f"failure_reason={final.failure_reason!r} "
            f"scores={scores} event_count={len(events)}"
        )

    assert final.status == "completed"
    assert scores
    assert any(s.value.passed for s in scores)
    assert RunId(run.id) in bundle.sandbox.destroyed
    assert RunId(run.id) in bundle.sandbox.provisioned
    assert len(events) >= 1

    # No orphan EvalForge sandbox containers for this run id.
    containers = live_engine.client.containers.list(all=True)
    orphans = [
        c
        for c in containers
        if c.labels.get("run_id") == run.id
        or (c.name or "").startswith(f"run-{run.id}")
    ]
    assert not orphans, f"orphan sandbox containers remain: {[c.name for c in orphans]}"
