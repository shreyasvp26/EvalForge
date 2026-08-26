"""Platform catalog use cases and Run pin validation."""

from __future__ import annotations

import pytest
from agent_eval_application.commands.platform import (
    CreatePlatformCommand,
    CreatePlatformDraftVersionCommand,
    PublishPlatformVersionCommand,
)
from agent_eval_application.commands.run import CreateRunCommand
from agent_eval_application.errors import ApplicationValidationError
from agent_eval_application.queries.queries import GetPlatformQuery, ListPlatformsQuery
from agent_eval_application.use_cases.platform import (
    CreatePlatform,
    CreatePlatformDraftVersion,
    GetPlatform,
    ListPlatforms,
    PublishPlatformVersion,
)
from agent_eval_application.use_cases.run import CreateRun

pytest_plugins = ("test_run_use_cases",)


def _run_command(world, platform_version_id: str) -> CreateRunCommand:
    return CreateRunCommand(
        actor=world["actor"],
        project_id=world["project_id"],
        case_id=world["case_id"],
        case_version_id=world["case_version_id"],
        prompt_version_id=world["prompt_version_id"],
        agent_id=world["agent_id"],
        agent_version_id=world["agent_version_id"],
        adapter_version_id=world["adapter_version_id"],
        grader_version_refs=((world["grader_id"], world["grader_version_id"]),),
        platform_version_id=platform_version_id,
    )


def _create_run(world, platform_version_id: str):
    return CreateRun(
        world["uow"],
        world["ids"],
        world["auth"],
        world["events"],
        world["queue"],
        world["idempotency"],
    ).execute(_run_command(world, platform_version_id))


def test_create_publish_list_and_get_platform(world) -> None:
    platform = CreatePlatform(
        world["uow"], world["ids"], world["auth"], world["events"]
    ).execute(CreatePlatformCommand(actor=world["actor"], name="Production Linux"))
    draft = CreatePlatformDraftVersion(
        world["uow"], world["ids"], world["auth"], world["events"]
    ).execute(
        CreatePlatformDraftVersionCommand(
            actor=world["actor"],
            platform_id=platform.id,
            label="2026.08",
            sandbox_policy={"network_mode": "isolated"},
            execution_policy={"runner": "docker"},
            timeout_policy={"default_timeout_seconds": "120"},
            environment_policy={"allowlist_ref": "prod-default"},
            grading_policy={"mode": "deterministic"},
        )
    )
    published = PublishPlatformVersion(
        world["uow"], world["auth"], world["events"]
    ).execute(
        PublishPlatformVersionCommand(
            actor=world["actor"], platform_id=platform.id, version_id=draft.id
        )
    )

    assert published.status == "active"
    assert _create_run(world, published.id).pins.platform_version_id == published.id
    assert (
        GetPlatform(world["uow"], world["auth"])
        .execute(GetPlatformQuery(actor=world["actor"], platform_id=platform.id))
        .active_version_id
        == published.id
    )
    assert platform.id in {
        item.id
        for item in ListPlatforms(world["uow"], world["auth"]).execute(
            ListPlatformsQuery(actor=world["actor"])
        )
    }


def test_create_run_rejects_unknown_platform_version(world) -> None:
    with pytest.raises(ApplicationValidationError) as exc_info:
        _create_run(world, "missing-platform-version")
    assert exc_info.value.code == "PLATFORM_VERSION_NOT_FOUND"


def test_create_run_rejects_draft_platform_version(world) -> None:
    platform = CreatePlatform(
        world["uow"], world["ids"], world["auth"], world["events"]
    ).execute(CreatePlatformCommand(actor=world["actor"], name="Draft Platform"))
    draft = CreatePlatformDraftVersion(
        world["uow"], world["ids"], world["auth"], world["events"]
    ).execute(
        CreatePlatformDraftVersionCommand(
            actor=world["actor"],
            platform_id=platform.id,
            label="draft",
        )
    )
    with pytest.raises(ApplicationValidationError) as exc_info:
        _create_run(world, draft.id)
    assert exc_info.value.code == "PLATFORM_VERSION_NOT_PINNABLE"
