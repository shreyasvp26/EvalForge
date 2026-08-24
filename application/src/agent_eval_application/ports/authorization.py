"""Authorization port — Project-scoped access checks.

API authenticates; Application authorizes (Backend Architecture §4 / §8).
"""

from __future__ import annotations

from typing import Protocol

from agent_eval_domain.common.ids import ProjectId

from agent_eval_application.common.actor import Actor


class AuthorizationPort(Protocol):
    """Enforces whether an Actor may perform Project-scoped operations."""

    def ensure_can_access_project(self, actor: Actor, project_id: ProjectId) -> None:
        """Raise AuthorizationError if the actor cannot read Project data."""

    def ensure_can_manage_project(self, actor: Actor, project_id: ProjectId) -> None:
        """Raise AuthorizationError if the actor cannot mutate Project data."""

    def ensure_can_create_project(self, actor: Actor) -> None:
        """Raise AuthorizationError if the actor cannot create Projects."""

    def grant_project_owner(self, actor: Actor, project_id: ProjectId) -> None:
        """Record Owner membership for a newly created Project.

        Must run inside the same Unit of Work as Project persistence so a
        failed grant rolls back the Project rather than leaving an orphan.
        """
