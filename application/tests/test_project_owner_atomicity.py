"""Project create + Owner membership atomicity."""

from __future__ import annotations

import pytest
from agent_eval_application.commands.project import CreateProjectCommand
from agent_eval_application.common.actor import Actor
from agent_eval_application.use_cases.project import CreateProject
from agent_eval_domain.common.ids import ProjectId
from fakes import (
    AllowAllAuth,
    InMemoryIdempotencyStore,
    InMemoryIdGenerator,
    InMemoryUnitOfWorkFactory,
    RecordingEventDispatcher,
    SharedStore,
)


class FailingOwnerAuth(AllowAllAuth):
    def grant_project_owner(self, actor: Actor, project_id: ProjectId) -> None:
        raise RuntimeError("membership store unavailable")


def test_create_project_grants_owner_before_commit() -> None:
    store = SharedStore()
    auth = AllowAllAuth()
    uc = CreateProject(
        InMemoryUnitOfWorkFactory(store),
        InMemoryIdGenerator("proj"),
        auth,
        RecordingEventDispatcher(),
        InMemoryIdempotencyStore(),
    )
    result = uc.execute(
        CreateProjectCommand(actor=Actor(id="user-1"), name="Alpha", description="d")
    )
    assert store.projects.get(ProjectId(result.id)).name == "Alpha"
    assert auth.granted_owners == [("user-1", result.id)]


def test_membership_failure_rolls_back_project() -> None:
    store = SharedStore()
    auth = FailingOwnerAuth()
    uc = CreateProject(
        InMemoryUnitOfWorkFactory(store),
        InMemoryIdGenerator("proj"),
        auth,
        RecordingEventDispatcher(),
    )
    with pytest.raises(RuntimeError, match="membership store unavailable"):
        uc.execute(
            CreateProjectCommand(
                actor=Actor(id="user-1"), name="Orphan", description="d"
            )
        )
    assert store.projects.list_all() == []
    assert auth.granted_owners == []


def test_idempotent_create_grants_owner_once() -> None:
    store = SharedStore()
    auth = AllowAllAuth()
    uc = CreateProject(
        InMemoryUnitOfWorkFactory(store),
        InMemoryIdGenerator("proj"),
        auth,
        RecordingEventDispatcher(),
        InMemoryIdempotencyStore(),
    )
    cmd = CreateProjectCommand(
        actor=Actor(id="user-1"),
        name="Alpha",
        idempotency_key="ik-owner",
    )
    first = uc.execute(cmd)
    second = uc.execute(cmd)
    assert first.id == second.id
    assert len(store.projects.list_all()) == 1
    # Replay must not re-grant (grant only runs on the first successful path).
    assert auth.granted_owners == [("user-1", first.id)]
