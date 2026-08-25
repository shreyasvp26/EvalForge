"""LintGrader — recorded linter exit codes."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from agent_eval_domain.execution.entities import Artifact, ExecutionEvent

from agent_eval_graders.objective._helpers import matching_shell
from agent_eval_graders.sdk.context import GradingContext
from agent_eval_graders.sdk.grader import BaseGrader
from agent_eval_graders.sdk.models import ProducedScore
from agent_eval_graders.sdk.result import produce_objective_score

DEFAULT_LINT_PATTERNS = (
    r"\bruff\b",
    r"\beslint\b",
    r"\bpylint\b",
    r"\bflake8\b",
    r"\bmypy\b",
    r"\bblack\s+--check\b",
    r"\bprettier\s+--check\b",
)


@dataclass
class LintGrader(BaseGrader):
    name: str = "lint"
    command_patterns: tuple[str, ...] = field(
        default_factory=lambda: DEFAULT_LINT_PATTERNS
    )

    def grade(
        self,
        context: GradingContext,
        events: Sequence[ExecutionEvent],
        artifacts: Sequence[Artifact],
    ) -> object:
        del artifacts
        context.check_timeout()
        matches = matching_shell(events, self.command_patterns)
        if not matches:
            return {"passed": False, "reason": "no lint command found in run record"}
        failed = [m for m in matches if m.exit_code not in (None, 0)]
        if failed:
            return {
                "passed": False,
                "reason": f"lint failed: {failed[-1].command}",
                "exit_code": failed[-1].exit_code,
            }
        if any(m.exit_code is None for m in matches):
            return {"passed": False, "reason": "lint command missing exit code"}
        return {"passed": True, "reason": "all lint commands exited 0"}

    def produce_scores(
        self,
        context: GradingContext,
        judgment: object,
    ) -> Sequence[ProducedScore]:
        return produce_objective_score(
            context,
            grader_name=self.name,
            judgment=judgment,
            evidence_keys=("exit_code",),
        )
