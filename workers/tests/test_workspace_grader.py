"""Tests for workspace file probes and workspace pytest execution."""

from __future__ import annotations

import pytest
from agent_eval_domain.common.ids import RunId
from agent_eval_graders.objective import ExpectedFileGrader, TestPassGrader
from agent_eval_sandbox.docker.sandbox import DockerSandbox
from agent_eval_sandbox.manager import SandboxManager
from agent_eval_sandbox.models import SandboxSpec
from agent_eval_workers.execution_engine.errors import RecoverableExecutionError
from agent_eval_workers.integration.grading_scheduler import GraderInvocationSpec
from agent_eval_workers.integration.registry import RunSandboxRegistry
from agent_eval_workers.integration.workspace_grader import (
    WorkspaceExpectedFileProbe,
    parse_workspace_test_command,
)
from docker_fakes import FakeDockerEngine


def test_parse_workspace_test_command_defaults() -> None:
    assert parse_workspace_test_command("workspace:") == (
        "python3",
        "-m",
        "pytest",
        "tests/",
        "-q",
    )
    assert parse_workspace_test_command("workspace:pytest -q") == ("pytest", "-q")


def _probe_with_workspace() -> (
    tuple[WorkspaceExpectedFileProbe, RunId, FakeDockerEngine]
):
    engine = FakeDockerEngine()
    manager = SandboxManager(runtime=DockerSandbox(engine=engine))
    registry = RunSandboxRegistry()
    run_id = RunId("run-workspace-test")
    handle = manager.create(
        SandboxSpec(image="evalforge/sandbox:local", working_dir="/workspace")
    )
    manager.start(handle)
    registry.register(run_id, handle)
    probe = WorkspaceExpectedFileProbe(
        manager=manager,
        sandboxes=registry,
        working_directory_factory=lambda _rid: "/workspace",
    )
    return probe, run_id, engine


def test_workspace_probe_runs_pytest_against_same_workspace() -> None:
    probe, run_id, engine = _probe_with_workspace()
    handle = probe.sandboxes.get(run_id)
    engine.seed_file(handle.container_id, "/workspace/calculator.py", b"x=1\n")
    engine.seed_file(
        handle.container_id,
        "/workspace/tests/test_calculator.py",
        b"def test_ok():\n    assert True\n",
    )

    specs = (
        GraderInvocationSpec(
            name="workspace_tests",
            grader_id="grader-test",
            grader_version_id="gv-test",
            factory=TestPassGrader,
            specification="workspace:python3 -m pytest tests/ -q",
        ),
    )
    probe.verify(run_id, specs)
    results = probe.workspace_results()
    assert "gv-test" in results
    assert results["gv-test"].passed is True

    engine.seed_file(
        handle.container_id,
        "/workspace/tests/test_calculator.py",
        b"def test_fail():\n    assert False\n",
    )
    engine.exec_exit_code = 1
    probe.verify(run_id, specs)
    assert probe.workspace_results()["gv-test"].passed is False


def test_workspace_probe_expected_file_missing_raises() -> None:
    probe, run_id, _engine = _probe_with_workspace()
    specs = (
        GraderInvocationSpec(
            name="expected",
            grader_id="grader-file",
            grader_version_id="gv-file",
            factory=lambda: ExpectedFileGrader(expected_paths=("missing.py",)),
            specification="missing.py",
        ),
    )
    with pytest.raises(RecoverableExecutionError, match="missing expected files"):
        probe.verify(run_id, specs)
