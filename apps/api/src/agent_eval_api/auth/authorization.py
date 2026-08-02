"""Authorization port adapters for the API Layer."""

from __future__ import annotations

from agent_eval_application.common.actor import Actor
from agent_eval_domain.common.ids import ProjectId

from agent_eval_api.auth.rbac import ProjectRbacAuthorization

__all__ = ["AllowAllAuthorization", "ProjectRbacAuthorization"]


class AllowAllAuthorization:
    """Permissive AuthorizationPort — tests / emergency bypass only."""

    def ensure_can_access_project(self, actor: Actor, project_id: ProjectId) -> None:
        return None

    def ensure_can_manage_project(self, actor: Actor, project_id: ProjectId) -> None:
        return None

    def ensure_can_create_project(self, actor: Actor) -> None:
        return None
