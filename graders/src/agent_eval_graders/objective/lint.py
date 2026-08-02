"""LintGrader — recorded linter exit codes."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from uuid import uuid4

from agent_eval_domain.common.ids import ScoreId
from agent_eval_domain.execution.entities import Artifact, ExecutionEvent

from agent_eval_graders.objective._helpers import matching_shell
from agent_eval_graders.sdk.context import GradingContext
from agent_eval_graders.sdk.grader import BaseGrader
from agent_eval_graders.sdk.models import ProducedScore, make_score

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
        data = judgment if isinstance(judgment, dict) else {}
        passed = bool(data.get("passed"))
        return (
            make_score(
                score_id=ScoreId(f"score-{uuid4().hex[:12]}"),
                run_id=context.reader.metadata().run_id,
                grader_id=context.grader_id,
                grader_version_id=context.grader_version_id,
                passed=passed,
                numeric=1.0 if passed else 0.0,
                reason=str(data.get("reason", "")),
                detail={"grader": self.name},
            ),
        )
