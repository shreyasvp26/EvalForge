"""Unit tests for PinBasedGraderResolver objective mapping."""

from __future__ import annotations

from agent_eval_graders.objective import (
    BuildSuccessGrader,
    DiffValidationGrader,
    ExitCodeGrader,
    ExpectedFileGrader,
    JSONOutputGrader,
    LintGrader,
    TestPassGrader,
)
from agent_eval_workers.integration.grader_resolver import _objective_factory


def _make(name: str, specification: str = ""):
    return _objective_factory(name=name, specification=specification)()


def test_objective_factory_maps_known_grader_names() -> None:
    assert isinstance(_make("build_success"), BuildSuccessGrader)
    assert isinstance(_make("test_pass"), TestPassGrader)
    assert isinstance(_make("lint"), LintGrader)
    assert isinstance(_make("exit_code"), ExitCodeGrader)
    assert isinstance(_make("diff_validation"), DiffValidationGrader)
    assert isinstance(_make("expected_file", "src/main.py"), ExpectedFileGrader)
    json_grader = _make("json_output", "score,status")
    assert isinstance(json_grader, JSONOutputGrader)
    assert json_grader.required_keys == ("score", "status")


def test_objective_factory_defaults_to_expected_file_paths() -> None:
    grader = _make("custom_objective", "lib/util.py,README.md")
    assert isinstance(grader, ExpectedFileGrader)
    assert grader.expected_paths == ("lib/util.py", "README.md")
