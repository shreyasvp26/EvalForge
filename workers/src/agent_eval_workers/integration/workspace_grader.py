"""Verify objective grader expectations against the live sandbox workspace.

Graders primarily consume execution events (architecture: no Sandbox refs in
GradingContext). This probe runs in the Worker composition root while the
sandbox still exists — before isolated grader invocations — so ExpectedFile
pins are checked against the same materialized workspace the agent modified.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from agent_eval_domain.common.ids import RunId
from agent_eval_graders.objective import ExpectedFileGrader
from agent_eval_sandbox.manager import SandboxManager
from agent_eval_sandbox.models import ExecutionRequest
from agent_eval_shared.log import get_logger

from agent_eval_workers.execution_engine.errors import RecoverableExecutionError
from agent_eval_workers.integration.grading_scheduler import GraderInvocationSpec
from agent_eval_workers.integration.registry import RunSandboxRegistry
from agent_eval_workers.lifecycle.triggers import FailureCause

logger = get_logger(__name__)

WorkspaceFactory = Callable[[RunId], str]


@dataclass(slots=True)
class WorkspaceExpectedFileProbe:
    """Fail closed when ExpectedFile paths are missing from the evaluation workspace."""

    manager: SandboxManager
    sandboxes: RunSandboxRegistry
    working_directory_factory: WorkspaceFactory

    def verify(
        self,
        run_id: RunId,
        specs: Sequence[GraderInvocationSpec],
    ) -> None:
        paths: list[str] = []
        for spec in specs:
            grader = spec.factory()
            if isinstance(grader, ExpectedFileGrader):
                paths.extend(grader.expected_paths)

        unique = tuple(dict.fromkeys(p for p in paths if p))
        if not unique:
            return

        handle = self.sandboxes.get(run_id)
        workspace = self.working_directory_factory(run_id).rstrip("/")
        missing: list[str] = []
        for relative in unique:
            target = (
                relative
                if relative.startswith("/")
                else f"{workspace}/{relative.lstrip('./')}"
            )
            result = self.manager.execute(
                handle,
                ExecutionRequest(
                    command=("test", "-e", target),
                    timeout_seconds=15.0,
                ),
            )
            if result.timed_out or result.exit_code != 0:
                missing.append(relative)

        if missing:
            logger.error(
                "workspace_expected_files_missing",
                run_id=run_id.value,
                workspace=workspace,
                missing=missing,
            )
            raise RecoverableExecutionError(
                "Grading workspace is missing expected files "
                f"{missing} under {workspace}; agent result does not match "
                "the materialized evaluation workspace",
                cause=FailureCause.WORKER_FAILURE,
            )
        logger.info(
            "workspace_expected_files_present",
            run_id=run_id.value,
            workspace=workspace,
            paths=list(unique),
        )
