"""Tests for pinned prompt resolution into Adapter execution."""

from __future__ import annotations

from agent_eval_application.common.actor import Actor
from agent_eval_application.queries.queries import GetRunQuery
from agent_eval_application.use_cases.case import ListCasesByProject
from agent_eval_application.use_cases.run import GetRun
from agent_eval_domain.common.ids import RunId
from agent_eval_workers.integration.prompt_resolver import (
    DEFAULT_PROMPT,
    PinnedPromptResolver,
)

pytest_plugins = ["test_run_use_cases"]


def test_pinned_prompt_resolver_returns_case_prompt(world) -> None:
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
            platform_version_id=world["platform_version_id"],
        )
    )

    resolver = PinnedPromptResolver(
        actor=world["actor"],
        get_run=GetRun(world["uow"], world["auth"]),
        list_cases=ListCasesByProject(world["uow"], world["auth"]),
    )
    assert resolver.resolve(RunId(run.id)) == "Fix it"


def test_pinned_prompt_resolver_falls_back_when_missing(world) -> None:
    class _MissingPromptRun:
        def execute(self, query: GetRunQuery):  # noqa: ANN001
            dto = GetRun(world["uow"], world["auth"]).execute(query)
            # Force an unknown prompt pin while keeping other fields valid.
            from dataclasses import replace

            pins = replace(dto.pins, prompt_version_id="prompt-does-not-exist")
            return replace(dto, pins=pins)

    resolver = PinnedPromptResolver(
        actor=world["actor"],
        get_run=_MissingPromptRun(),
        list_cases=ListCasesByProject(world["uow"], world["auth"]),
    )
    # Need a real run id for GetRun path in fallback test — create then override.
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
            platform_version_id=world["platform_version_id"],
        )
    )
    assert resolver.resolve(RunId(run.id)) == DEFAULT_PROMPT


def test_process_worker_uses_pinned_prompt(world) -> None:
    from agent_eval_application.commands.run import CreateRunCommand
    from agent_eval_application.use_cases.run import CreateRun
    from agent_eval_sandbox.docker.fake import FakeDockerEngine
    from agent_eval_workers.integration.composition import default_claude_factory
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
            platform_version_id=world["platform_version_id"],
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
        adapter_factory=default_claude_factory(),
        actor=Actor(id="system-worker"),
        auth=WorkerAuthorization(),
        sandbox_mode="fake",
        adapter_mode="deterministic",
    )
    original_start = bundle.adapter.start

    def capturing_start(run_id: RunId) -> None:
        original_start(run_id)
        session = bundle.adapter._sessions[run_id.value]
        seen.append(session.context.prompt)

    bundle.adapter.start = capturing_start  # type: ignore[method-assign]
    bundle.worker.run_once(block=False)
    assert seen == ["Fix it"]
