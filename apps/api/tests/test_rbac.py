"""Project-aware RBAC tests."""

from __future__ import annotations

import pytest
from agent_eval_api.auth.rbac import ProjectRbacAuthorization
from agent_eval_api.composition import build_api_container
from agent_eval_application.common.actor import Actor
from agent_eval_application.errors import AuthorizationError
from agent_eval_domain.common.ids import ProjectId
from agent_eval_infrastructure import RuntimeProfile, build_infrastructure
from agent_eval_infrastructure.auth import (
    ROLE_RANK,
    InMemoryMembershipStore,
    ProjectRole,
)
from agent_eval_infrastructure.config import InfrastructureSettings


@pytest.fixture
def store() -> InMemoryMembershipStore:
    return InMemoryMembershipStore()


@pytest.fixture
def auth(store: InMemoryMembershipStore) -> ProjectRbacAuthorization:
    return ProjectRbacAuthorization(store)


def test_role_rank_ordering() -> None:
    assert ROLE_RANK[ProjectRole.VIEWER] < ROLE_RANK[ProjectRole.MAINTAINER]
    assert ROLE_RANK[ProjectRole.MAINTAINER] < ROLE_RANK[ProjectRole.ADMIN]
    assert ROLE_RANK[ProjectRole.ADMIN] < ROLE_RANK[ProjectRole.OWNER]


def test_create_project_allowed_for_any_authenticated_actor(
    auth: ProjectRbacAuthorization,
) -> None:
    auth.ensure_can_create_project(Actor(id="anyone"))


def test_access_denied_without_membership(auth: ProjectRbacAuthorization) -> None:
    with pytest.raises(AuthorizationError) as exc:
        auth.ensure_can_access_project(Actor(id="a1"), ProjectId("p1"))
    assert exc.value.details["actual_role"] is None


@pytest.mark.parametrize(
    ("role", "can_access", "can_manage"),
    [
        (ProjectRole.VIEWER, True, False),
        (ProjectRole.MAINTAINER, True, True),
        (ProjectRole.ADMIN, True, True),
        (ProjectRole.OWNER, True, True),
    ],
)
def test_role_permissions(
    auth: ProjectRbacAuthorization,
    store: InMemoryMembershipStore,
    role: ProjectRole,
    can_access: bool,
    can_manage: bool,
) -> None:
    actor = Actor(id="a1")
    project_id = ProjectId("p1")
    store.upsert(actor_id=actor.id, project_id=project_id.value, role=role)

    if can_access:
        auth.ensure_can_access_project(actor, project_id)
    else:
        with pytest.raises(AuthorizationError):
            auth.ensure_can_access_project(actor, project_id)

    if can_manage:
        auth.ensure_can_manage_project(actor, project_id)
    else:
        with pytest.raises(AuthorizationError):
            auth.ensure_can_manage_project(actor, project_id)


def test_grant_owner_membership(auth: ProjectRbacAuthorization, store) -> None:
    auth.grant(actor_id="owner-1", project_id="proj-9")
    assert store.get_role(actor_id="owner-1", project_id="proj-9") is ProjectRole.OWNER


def test_build_api_container_uses_rbac(settings) -> None:
    infra_settings = InfrastructureSettings(
        environment="test",
        database_url="sqlite+pysqlite:///:memory:",
    )
    container = build_api_container(
        settings=settings,
        infrastructure=build_infrastructure(
            settings=infra_settings,
            profile=RuntimeProfile.MEMORY,
        ),
    )
    try:
        assert isinstance(container.auth, ProjectRbacAuthorization)
        assert isinstance(container.memberships, InMemoryMembershipStore)
        actor = Actor(id="creator")
        container.auth.ensure_can_create_project(actor)
        with pytest.raises(AuthorizationError):
            container.auth.ensure_can_access_project(actor, ProjectId("missing"))
        container.auth.grant(actor_id=actor.id, project_id="missing")
        container.auth.ensure_can_access_project(actor, ProjectId("missing"))
        container.auth.ensure_can_manage_project(actor, ProjectId("missing"))
    finally:
        container.dispose()
