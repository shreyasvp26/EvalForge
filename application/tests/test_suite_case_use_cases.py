"""Suite and Case use-case orchestration tests."""

from __future__ import annotations

import pytest
from agent_eval_application.commands.case import (
    CreateCaseCommand,
    CreateCaseDraftVersionCommand,
    CreatePromptDraftVersionCommand,
    PublishCaseVersionCommand,
    PublishPromptVersionCommand,
)
from agent_eval_application.commands.project import CreateProjectCommand
from agent_eval_application.commands.suite import (
    CreateSuiteCommand,
    CreateSuiteDraftVersionCommand,
    PublishSuiteVersionCommand,
    SuiteCompositionEntryInput,
)
from agent_eval_application.common.actor import Actor
from agent_eval_application.use_cases.case import (
    CreateCase,
    CreateCaseDraftVersion,
    CreatePromptDraftVersion,
    PublishCaseVersion,
    PublishPromptVersion,
)
from agent_eval_application.use_cases.project import CreateProject
from agent_eval_application.use_cases.suite import (
    CreateSuite,
    CreateSuiteDraftVersion,
    PublishSuiteVersion,
)
from fakes import (
    AllowAllAuth,
    InMemoryIdGenerator,
    InMemoryUnitOfWorkFactory,
    RecordingEventDispatcher,
    SharedStore,
)


@pytest.fixture
def harness():
    store = SharedStore()
    ids = InMemoryIdGenerator("x")
    uow = InMemoryUnitOfWorkFactory(store)
    auth = AllowAllAuth()
    events = RecordingEventDispatcher()
    actor = Actor(id="user-1")
    project = CreateProject(uow, ids, auth, events).execute(
        CreateProjectCommand(actor=actor, name="P")
    )
    return {
        "uow": uow,
        "ids": ids,
        "auth": auth,
        "events": events,
        "actor": actor,
        "project_id": project.id,
    }


def test_suite_create_draft_and_publish(harness):
    suite = CreateSuite(
        harness["uow"], harness["ids"], harness["auth"], harness["events"]
    ).execute(
        CreateSuiteCommand(
            actor=harness["actor"],
            project_id=harness["project_id"],
            name="Suite A",
        )
    )
    assert suite.project_id == harness["project_id"]

    # Need a published case version for composition — create minimal case path.
    case = CreateCase(
        harness["uow"], harness["ids"], harness["auth"], harness["events"]
    ).execute(
        CreateCaseCommand(
            actor=harness["actor"],
            project_id=harness["project_id"],
            name="Case A",
        )
    )
    prompt_v = CreatePromptDraftVersion(
        harness["uow"], harness["ids"], harness["auth"], harness["events"]
    ).execute(
        CreatePromptDraftVersionCommand(
            actor=harness["actor"],
            case_id=case.id,
            content="Do the thing",
        )
    )
    PublishPromptVersion(harness["uow"], harness["auth"], harness["events"]).execute(
        PublishPromptVersionCommand(
            actor=harness["actor"],
            case_id=case.id,
            version_id=prompt_v.id,
        )
    )
    case_v = CreateCaseDraftVersion(
        harness["uow"], harness["ids"], harness["auth"], harness["events"]
    ).execute(
        CreateCaseDraftVersionCommand(
            actor=harness["actor"],
            case_id=case.id,
            description="Task description",
            repository_url="https://example.com/r.git",
            commit_sha="abc123",
            expected_checks=("pytest",),
            applicable_grader_ids=(),
            prompt_version_id=prompt_v.id,
        )
    )
    published_case_v = PublishCaseVersion(
        harness["uow"], harness["auth"], harness["events"]
    ).execute(
        PublishCaseVersionCommand(
            actor=harness["actor"],
            case_id=case.id,
            version_id=case_v.id,
        )
    )

    draft = CreateSuiteDraftVersion(
        harness["uow"], harness["ids"], harness["auth"], harness["events"]
    ).execute(
        CreateSuiteDraftVersionCommand(
            actor=harness["actor"],
            suite_id=suite.id,
            composition=(
                SuiteCompositionEntryInput(
                    case_version_id=published_case_v.id,
                    position=0,
                    case_project_id=harness["project_id"],
                ),
            ),
        )
    )
    assert draft.status == "draft"

    published = PublishSuiteVersion(
        harness["uow"], harness["auth"], harness["events"]
    ).execute(
        PublishSuiteVersionCommand(
            actor=harness["actor"],
            suite_id=suite.id,
            version_id=draft.id,
        )
    )
    assert published.status == "active"
