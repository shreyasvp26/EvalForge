"""Project-aware RBAC implementing Application ``AuthorizationPort``.

Policy lives here (API composition); membership rows live in Infrastructure.
Application use cases are unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass

from agent_eval_application.common.actor import Actor
from agent_eval_application.errors import AuthorizationError
from agent_eval_domain.common.ids import ProjectId
from agent_eval_infrastructure.auth import (
    ROLE_RANK,
    MembershipStore,
    ProjectRole,
)


@dataclass(slots=True)
class ProjectRbacAuthorization:
    """Enforce Owner / Admin / Maintainer / Viewer on Project operations."""

    memberships: MembershipStore

    def ensure_can_access_project(self, actor: Actor, project_id: ProjectId) -> None:
        self._require_at_least(actor, project_id, ProjectRole.VIEWER)

    def ensure_can_manage_project(self, actor: Actor, project_id: ProjectId) -> None:
        self._require_at_least(actor, project_id, ProjectRole.MAINTAINER)

    def ensure_can_create_project(self, actor: Actor) -> None:
        # Any authenticated Actor may create a Project; CreateProject grants
        # Owner membership inside the same Unit of Work as persistence.
        del actor

    def grant_project_owner(self, actor: Actor, project_id: ProjectId) -> None:
        self.grant(actor_id=actor.id, project_id=project_id.value)

    def grant(
        self,
        *,
        actor_id: str,
        project_id: str,
        role: ProjectRole = ProjectRole.OWNER,
    ) -> None:
        self.memberships.upsert(
            actor_id=actor_id,
            project_id=project_id,
            role=role,
        )

    def _require_at_least(
        self,
        actor: Actor,
        project_id: ProjectId,
        minimum: ProjectRole,
    ) -> None:
        role = self.memberships.get_role(
            actor_id=actor.id,
            project_id=project_id.value,
        )
        if role is None or ROLE_RANK[role] < ROLE_RANK[minimum]:
            raise AuthorizationError(
                "Actor is not permitted for this Project",
                details={
                    "actor_id": actor.id,
                    "project_id": project_id.value,
                    "required_role": minimum.value,
                    "actual_role": None if role is None else role.value,
                },
            )
