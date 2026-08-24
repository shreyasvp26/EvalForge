"""Worker-process authorization — system actor may advance Run lifecycle.

Control-plane RBAC still protects human API callers. The worker Actor is a
trusted process identity that must be able to StartRun / RecordScore / etc.
for any Project whose Run it claimed from the queue.
"""

from __future__ import annotations

from dataclasses import dataclass

from agent_eval_application.common.actor import Actor
from agent_eval_application.errors import AuthorizationError
from agent_eval_domain.common.ids import ProjectId


@dataclass(slots=True)
class WorkerAuthorization:
    """Allow the configured system-worker Actor full Project access."""

    system_actor_id: str = "system-worker"

    def ensure_can_access_project(self, actor: Actor, project_id: ProjectId) -> None:
        del project_id
        self._require_system(actor)

    def ensure_can_manage_project(self, actor: Actor, project_id: ProjectId) -> None:
        del project_id
        self._require_system(actor)

    def ensure_can_create_project(self, actor: Actor) -> None:
        self._require_system(actor)

    def grant_project_owner(self, actor: Actor, project_id: ProjectId) -> None:
        del actor, project_id
        raise AuthorizationError(
            "Worker process cannot grant Project ownership",
            details={"actor_id": self.system_actor_id},
        )

    def _require_system(self, actor: Actor) -> None:
        if actor.id != self.system_actor_id:
            raise AuthorizationError(
                "Only the system worker Actor may use WorkerAuthorization",
                details={
                    "actor_id": actor.id,
                    "expected": self.system_actor_id,
                },
            )
