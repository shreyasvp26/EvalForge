"""Authorization port adapter for the Control Plane composition root.

Real Project-scoped policies are Application-owned and remain TODO.
This adapter permits all authenticated Actors so the API can exercise
use cases end-to-end without embedding policy in Infrastructure.
"""

from __future__ import annotations

from agent_eval_application.common.actor import Actor
from agent_eval_domain.common.ids import ProjectId


class AllowAllAuthorization:
    """Permissive AuthorizationPort — replace with real policy later."""

    def ensure_can_access_project(self, actor: Actor, project_id: ProjectId) -> None:
        return None

    def ensure_can_manage_project(self, actor: Actor, project_id: ProjectId) -> None:
        return None

    def ensure_can_create_project(self, actor: Actor) -> None:
        return None
