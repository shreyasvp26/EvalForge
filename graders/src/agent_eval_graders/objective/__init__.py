"""Objective grader family — deterministic measurement of recorded signals."""

from __future__ import annotations

from agent_eval_graders.objective.build_success import BuildSuccessGrader
from agent_eval_graders.objective.diff_validation import DiffValidationGrader
from agent_eval_graders.objective.exit_code import ExitCodeGrader
from agent_eval_graders.objective.expected_file import ExpectedFileGrader
from agent_eval_graders.objective.json_output import JSONOutputGrader
from agent_eval_graders.objective.lint import LintGrader
from agent_eval_graders.objective.test_pass import TestPassGrader
from agent_eval_graders.sdk.registry import GraderRegistry


def register_objective_graders(registry: GraderRegistry) -> GraderRegistry:
    """Register all built-in objective graders on ``registry``."""
    registry.register("build_success", BuildSuccessGrader)
    registry.register("exit_code", ExitCodeGrader)
    registry.register("test_pass", TestPassGrader)
    registry.register("lint", LintGrader)
    registry.register("expected_file", ExpectedFileGrader)
    registry.register("diff_validation", DiffValidationGrader)
    registry.register("json_output", JSONOutputGrader)
    return registry


def default_objective_registry() -> GraderRegistry:
    return register_objective_graders(GraderRegistry())


__all__ = [
    "BuildSuccessGrader",
    "DiffValidationGrader",
    "ExitCodeGrader",
    "ExpectedFileGrader",
    "JSONOutputGrader",
    "LintGrader",
    "TestPassGrader",
    "default_objective_registry",
    "register_objective_graders",
]
