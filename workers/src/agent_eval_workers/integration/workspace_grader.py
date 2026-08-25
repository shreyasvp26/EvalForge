"""Verify objective grader expectations against the live sandbox workspace.

Graders primarily consume execution events (architecture: no Sandbox refs in
GradingContext). This probe runs in the Worker composition root while the
sandbox still exists — before isolated grader invocations — so ExpectedFile
pins are checked against the same materialized workspace the agent modified,
and workspace test commands run against that same workspace.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field

from agent_eval_domain.common.ids import RunId
from agent_eval_graders.objective import ExpectedFileGrader, TestPassGrader
from agent_eval_sandbox.manager import SandboxManager
from agent_eval_sandbox.models import ExecutionRequest
from agent_eval_shared.log import get_logger

from agent_eval_workers.execution_engine.errors import RecoverableExecutionError
from agent_eval_workers.integration.grading_scheduler import GraderInvocationSpec
from agent_eval_workers.integration.registry import RunSandboxRegistry
from agent_eval_workers.lifecycle.triggers import FailureCause

logger = get_logger(__name__)

WorkspaceFactory = Callable[[RunId], str]

_WORKSPACE_PREFIX = "workspace:"
_DEFAULT_PYTEST = ("python3", "-m", "pytest", "tests/", "-q")


def parse_workspace_test_command(specification: str) -> tuple[str, ...] | None:
    """Return a shell command tuple when *specification* requests workspace tests."""
    raw = specification.strip()
    if not raw.lower().startswith(_WORKSPACE_PREFIX):
        return None
    command_text = raw[len(_WORKSPACE_PREFIX) :].strip()
    if not command_text:
        return _DEFAULT_PYTEST
    return tuple(command_text.split())


@dataclass(slots=True)
class WorkspaceTestResult:
    """Outcome of executing a test command inside the evaluation workspace."""

    grader_version_id: str
    command: tuple[str, ...]
    exit_code: int
    timed_out: bool
    stdout: str
    stderr: str

    @property
    def passed(self) -> bool:
        return not self.timed_out and self.exit_code == 0


@dataclass(slots=True)
class WorkspaceExpectedFileProbe:
    """Fail closed when ExpectedFile paths are missing from the evaluation workspace."""

    manager: SandboxManager
    sandboxes: RunSandboxRegistry
    working_directory_factory: WorkspaceFactory
    workspace_test_results: dict[str, WorkspaceTestResult] = field(default_factory=dict)

    def verify(
        self,
        run_id: RunId,
        specs: Sequence[GraderInvocationSpec],
    ) -> None:
        self._verify_expected_files(run_id, specs)
        self._run_workspace_tests(run_id, specs)

    def workspace_results(self) -> Mapping[str, WorkspaceTestResult]:
        return dict(self.workspace_test_results)

    def _verify_expected_files(
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

    def _run_workspace_tests(
        self,
        run_id: RunId,
        specs: Sequence[GraderInvocationSpec],
    ) -> None:
        self.workspace_test_results.clear()
        commands: list[tuple[str, tuple[str, ...]]] = []
        for spec in specs:
            grader = spec.factory()
            if not isinstance(grader, TestPassGrader):
                continue
            command = parse_workspace_test_command(spec.specification)
            if command is None:
                continue
            commands.append((spec.grader_version_id, command))

        if not commands:
            return

        handle = self.sandboxes.get(run_id)
        workspace = self.working_directory_factory(run_id).rstrip("/")
        for version_id, command in commands:
            result = self.manager.execute(
                handle,
                ExecutionRequest(
                    command=command,
                    working_dir=workspace,
                    timeout_seconds=120.0,
                ),
            )
            record = WorkspaceTestResult(
                grader_version_id=version_id,
                command=command,
                exit_code=result.exit_code,
                timed_out=result.timed_out,
                stdout=result.stdout,
                stderr=result.stderr,
            )
            self.workspace_test_results[version_id] = record
            logger.info(
                "workspace_test_executed",
                run_id=run_id.value,
                workspace=workspace,
                command=list(command),
                exit_code=result.exit_code,
                timed_out=result.timed_out,
            )
