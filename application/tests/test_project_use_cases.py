"""Application Layer unit tests — project orchestration."""

from __future__ import annotations

import pytest
from agent_eval_application.commands.project import (
    CreateProjectCommand,
    DeprecateProjectCommand,
    RenameProjectCommand,
)
from agent_eval_application.common.actor import Actor
from agent_eval_application.errors import (
    ApplicationValidationError,
    AuthorizationError,
    NotFoundApplicationError,
)
from agent_eval_application.queries.queries import GetProjectQuery
from agent_eval_application.use_cases.project import (
    CreateProject,
    DeprecateProject,
    GetProject,
    RenameProject,
)
from fakes import (
    AllowAllAuth,
    DenyAllAuth,
    InMemoryIdempotencyStore,
    InMemoryIdGenerator,
    InMemoryUnitOfWorkFactory,
    RecordingEventDispatcher,
    SharedStore,
)


@pytest.fixture
def harness():
    store = SharedStore()
    return {
        "store": store,
        "uow": InMemoryUnitOfWorkFactory(store),
        "ids": InMemoryIdGenerator("proj"),
        "auth": AllowAllAuth(),
        "events": RecordingEventDispatcher(),
        "idempotency": InMemoryIdempotencyStore(),
        "actor": Actor(id="user-1"),
    }


def test_create_project_persists_and_returns_dto(harness):
    uc = CreateProject(
        harness["uow"],
        harness["ids"],
        harness["auth"],
        harness["events"],
        harness["idempotency"],
    )
    result = uc.execute(
        CreateProjectCommand(actor=harness["actor"], name="Alpha", description="d")
    )
    assert result.name == "Alpha"
    assert result.id == "proj-1"
    loaded = GetProject(harness["uow"], harness["auth"]).execute(
        GetProjectQuery(actor=harness["actor"], project_id=result.id)
    )
    assert loaded.id == result.id


def test_create_project_rejects_blank_name(harness):
    uc = CreateProject(
        harness["uow"], harness["ids"], harness["auth"], harness["events"]
    )
    with pytest.raises(ApplicationValidationError):
        uc.execute(CreateProjectCommand(actor=harness["actor"], name="  "))


def test_create_project_authorization(harness):
    uc = CreateProject(harness["uow"], harness["ids"], DenyAllAuth(), harness["events"])
    with pytest.raises(AuthorizationError):
        uc.execute(CreateProjectCommand(actor=harness["actor"], name="X"))


def test_create_project_idempotency_replays(harness):
    uc = CreateProject(
        harness["uow"],
        harness["ids"],
        harness["auth"],
        harness["events"],
        harness["idempotency"],
    )
    cmd = CreateProjectCommand(
        actor=harness["actor"],
        name="Alpha",
        idempotency_key="ik-1",
    )
    first = uc.execute(cmd)
    second = uc.execute(cmd)
    assert first.id == second.id
    assert harness["ids"]._n == 1  # noqa: SLF001 — only one id minted


def test_rename_and_deprecate_project(harness):
    created = CreateProject(
        harness["uow"], harness["ids"], harness["auth"], harness["events"]
    ).execute(CreateProjectCommand(actor=harness["actor"], name="Alpha"))

    renamed = RenameProject(harness["uow"], harness["auth"], harness["events"]).execute(
        RenameProjectCommand(actor=harness["actor"], project_id=created.id, name="Beta")
    )
    assert renamed.name == "Beta"

    deprecated = DeprecateProject(
        harness["uow"], harness["auth"], harness["events"]
    ).execute(DeprecateProjectCommand(actor=harness["actor"], project_id=created.id))
    assert deprecated.status == "deprecated"


def test_get_missing_project_translates_domain_error(harness):
    with pytest.raises(NotFoundApplicationError) as exc_info:
        GetProject(harness["uow"], harness["auth"]).execute(
            GetProjectQuery(actor=harness["actor"], project_id="missing")
        )
    assert exc_info.value.code == "NOT_FOUND"
