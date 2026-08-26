"""Publish passed evaluations to GitHub while the sandbox is still alive."""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from dataclasses import dataclass

from agent_eval_application.common.actor import Actor
from agent_eval_application.use_cases.publish_run import (
    PublishEvaluationRun,
    PublishEvaluationRunCommand,
)
from agent_eval_domain.common.ids import RunId

from agent_eval_workers.integration.workspace_capture import SandboxWorkspaceCapture

logger = logging.getLogger(__name__)

GetRunDto = Callable[[RunId], object]


@dataclass(slots=True)
class EvaluationPublisher:
    """Lifecycle hook: after CompleteRun, before sandbox.destroy."""

    publish_run: PublishEvaluationRun
    capture: SandboxWorkspaceCapture
    get_run: GetRunDto
    system_actor: Actor

    def publish_if_eligible(self, run_id: RunId) -> None:
        if os.environ.get("EVALFORGE_AUTO_PUBLISH_ON_PASS", "1").strip() in {
            "0",
            "false",
            "no",
        }:
            return
        try:
            run = self.get_run(run_id)
        except Exception:  # noqa: BLE001
            logger.exception(
                "publication_get_run_failed", extra={"run_id": run_id.value}
            )
            return

        runtime = dict(getattr(run, "runtime_request", None) or {})
        if runtime.get("auto_publish_on_pass", "1").strip() in {"0", "false", "no"}:
            return

        actor_id = (runtime.get("requested_by_actor_id") or "").strip()
        actor = Actor(id=actor_id) if actor_id else self.system_actor

        base_sha = ""
        # Prefer provenance-ish metadata; PublishEvaluationRun resolves from case.
        changes = self.capture.capture_changes(run_id, base_commit_sha=base_sha or None)
        try:
            result = self.publish_run.execute(
                PublishEvaluationRunCommand(
                    actor=actor,
                    run_id=run_id.value,
                    changes=changes,
                    github_connection_id=runtime.get("github_connection_id") or None,
                )
            )
            logger.info(
                "publication_finished",
                extra={
                    "run_id": run_id.value,
                    "status": result.publication.get("status"),
                    "pr": result.publication.get("pull_request_url"),
                },
            )
        except Exception:  # noqa: BLE001 — never fail the evaluation path
            logger.exception(
                "publication_unexpected_error",
                extra={"run_id": run_id.value},
            )
