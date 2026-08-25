"""Tests for pin → adapter registry resolution (no silent Claude fallback)."""

from __future__ import annotations

import pytest
from agent_eval_application.common.actor import Actor
from agent_eval_application.use_cases.agent import ListAdapters
from agent_eval_application.use_cases.run import GetRun
from agent_eval_domain.common.ids import RunId
from agent_eval_workers.integration.adapter_registry import (
    CLAUDE_CODE,
    CURSOR,
    AdapterRegistry,
    AdapterResolutionError,
    PinnedAdapterResolver,
    default_adapter_registry,
    normalize_adapter_key,
    resolve_adapter_mode,
)

pytest_plugins = ["test_run_use_cases"]


def test_normalize_adapter_key_maps_known_names() -> None:
    assert normalize_adapter_key("claude_code") == CLAUDE_CODE
    assert normalize_adapter_key("Claude Code") == CLAUDE_CODE
    assert normalize_adapter_key("cursor") == CURSOR
    assert normalize_adapter_key("unknown-vendor") is None


def test_resolve_adapter_mode_live_and_deterministic() -> None:
    assert resolve_adapter_mode("live") == "live"
    assert resolve_adapter_mode("claude") == "live"
    assert resolve_adapter_mode("deterministic") == "deterministic"
    with pytest.raises(AdapterResolutionError):
        resolve_adapter_mode("mystery")


def test_registry_resolves_claude_deterministic() -> None:
    registry = default_adapter_registry()
    factory = registry.resolve(CLAUDE_CODE, mode="deterministic")
    adapter = factory()
    assert adapter.name == "claude_code"


def test_registry_live_claude_requires_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    registry = default_adapter_registry()
    with pytest.raises(AdapterResolutionError, match="ANTHROPIC_API_KEY"):
        registry.resolve(CLAUDE_CODE, mode="live")


def test_registry_live_claude_with_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")
    registry = default_adapter_registry()
    factory = registry.resolve(CLAUDE_CODE, mode="live")
    assert factory().name == "claude_code"


def test_registry_does_not_fallback_unsupported_key() -> None:
    registry = AdapterRegistry()
    registry.register_live(CLAUDE_CODE, lambda: object())  # type: ignore[arg-type]
    with pytest.raises(AdapterResolutionError, match="cursor"):
        registry.resolve(CURSOR, mode="live")


def test_pinned_adapter_resolver_resolves_claude(world) -> None:
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

    resolver = PinnedAdapterResolver(
        actor=world["actor"],
        get_run=GetRun(world["uow"], world["auth"]),
        list_adapters=ListAdapters(world["uow"], world["auth"]),
        mode="deterministic",
    )
    key, name, version_id = resolver.resolve_key(RunId(run.id))
    assert key == CLAUDE_CODE
    assert name == "claude_code"
    assert version_id == world["adapter_version_id"]
    factory = resolver.resolve_factory(RunId(run.id))
    assert factory().name == "claude_code"


def test_pinned_adapter_resolver_rejects_unmapped_name(world) -> None:
    from dataclasses import replace

    from agent_eval_application.commands.agent import (
        CreateAdapterCommand,
        CreateAdapterDraftVersionCommand,
        CreateAgentCommand,
        PublishAdapterVersionCommand,
    )
    from agent_eval_application.commands.run import CreateRunCommand
    from agent_eval_application.use_cases.agent import (
        CreateAdapter,
        CreateAdapterDraftVersion,
        CreateAgent,
        PublishAdapterVersion,
    )
    from agent_eval_application.use_cases.run import CreateRun

    agent = CreateAgent(
        world["uow"], world["ids"], world["auth"], world["events"]
    ).execute(CreateAgentCommand(actor=world["actor"], name="Other Agent"))
    adapter = CreateAdapter(
        world["uow"], world["ids"], world["auth"], world["events"]
    ).execute(
        CreateAdapterCommand(
            actor=world["actor"],
            agent_id=agent.id,
            name="totally-unsupported-vendor",
        )
    )
    adv = CreateAdapterDraftVersion(
        world["uow"], world["ids"], world["auth"], world["events"]
    ).execute(
        CreateAdapterDraftVersionCommand(
            actor=world["actor"], adapter_id=adapter.id, label="1.0"
        )
    )
    adv = PublishAdapterVersion(world["uow"], world["auth"], world["events"]).execute(
        PublishAdapterVersionCommand(
            actor=world["actor"], adapter_id=adapter.id, version_id=adv.id
        )
    )

    class _RunWithBadAdapter:
        def execute(self, query):  # noqa: ANN001
            dto = GetRun(world["uow"], world["auth"]).execute(query)
            pins = replace(dto.pins, adapter_version_id=adv.id)
            return replace(dto, pins=pins)

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

    resolver = PinnedAdapterResolver(
        actor=world["actor"],
        get_run=_RunWithBadAdapter(),
        list_adapters=ListAdapters(world["uow"], world["auth"]),
        mode="deterministic",
    )
    with pytest.raises(AdapterResolutionError, match="does not map"):
        resolver.resolve_key(RunId(run.id))


def test_process_worker_uses_pin_registry_without_factory_override(world) -> None:
    from agent_eval_application.commands.run import CreateRunCommand
    from agent_eval_application.use_cases.run import CreateRun
    from agent_eval_sandbox.docker.fake import FakeDockerEngine
    from agent_eval_workers.execution_engine import EngineOutcomeKind
    from agent_eval_workers.integration.process import build_production_worker
    from agent_eval_workers.integration.worker_auth import WorkerAuthorization
    from agent_eval_workers.worker.memory_queue import InMemoryWorkerQueue

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

    seen: list[str] = []
    bundle = build_production_worker(
        queue=queue,
        uow_factory=world["uow"],
        ids=world["ids"],
        events=world["events"],
        docker_engine=FakeDockerEngine(),
        actor=Actor(id="system-worker"),
        auth=WorkerAuthorization(),
        sandbox_mode="fake",
        adapter_mode="deterministic",
    )
    original_start = bundle.adapter.start

    def capturing_start(run_id: RunId) -> None:
        original_start(run_id)
        session = bundle.adapter._sessions[run_id.value]
        seen.append(session.adapter.name)

    bundle.adapter.start = capturing_start  # type: ignore[method-assign]
    result = bundle.worker.run_once(block=False)
    assert result is not None
    assert result.kind is EngineOutcomeKind.COMPLETED
    assert seen == ["claude_code"]


def test_process_worker_fails_live_without_credentials(
    world, monkeypatch: pytest.MonkeyPatch
) -> None:
    from agent_eval_application.commands.run import CreateRunCommand
    from agent_eval_application.queries.queries import GetRunQuery
    from agent_eval_application.use_cases.run import CreateRun, GetRun
    from agent_eval_sandbox.docker.fake import FakeDockerEngine
    from agent_eval_workers.integration.process import build_production_worker
    from agent_eval_workers.integration.worker_auth import WorkerAuthorization
    from agent_eval_workers.lifecycle.triggers import FailureCause
    from agent_eval_workers.worker.memory_queue import InMemoryWorkerQueue

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
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
    bundle = build_production_worker(
        queue=queue,
        uow_factory=world["uow"],
        ids=world["ids"],
        events=world["events"],
        docker_engine=FakeDockerEngine(),
        actor=Actor(id="system-worker"),
        auth=WorkerAuthorization(),
        sandbox_mode="fake",
        adapter_mode="live",
        max_attempts=1,
    )
    result = bundle.worker.run_once(block=False)
    assert result is not None
    assert result.failure_cause is FailureCause.ADAPTER_FAILURE
    assert result.detail is None or "ANTHROPIC_API_KEY" in (result.detail or "")
    dto = GetRun(world["uow"], world["auth"]).execute(
        GetRunQuery(actor=world["actor"], run_id=run.id)
    )
    assert dto.status in {"failed", "cancelled"}
    assert dto.failure_reason
    assert "ANTHROPIC_API_KEY" in dto.failure_reason
