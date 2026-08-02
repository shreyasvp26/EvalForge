"""TestPassGrader — recorded test-runner exit codes."""

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

DEFAULT_TEST_PATTERNS = (
    r"\bpytest\b",
    r"\bnpm\s+test\b",
    r"\bpnpm\s+test\b",
    r"\byarn\s+test\b",
    r"\bgo\s+test\b",
    r"\bcargo\s+test\b",
    r"\bmvn\s+test\b",
    r"\bvitest\b",
)


@dataclass
class TestPassGrader(BaseGrader):
    """Deterministic test-runner exit-code grader."""

    __test__ = False  # prevent pytest collecting this grader class
    name: str = "test_pass"
    command_patterns: tuple[str, ...] = field(
        default_factory=lambda: DEFAULT_TEST_PATTERNS
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
            return {"passed": False, "reason": "no test command found in run record"}
        failed = [m for m in matches if m.exit_code not in (None, 0)]
        if failed:
            return {
                "passed": False,
                "reason": f"tests failed: {failed[-1].command}",
                "exit_code": failed[-1].exit_code,
            }
        if any(m.exit_code is None for m in matches):
            return {"passed": False, "reason": "test command missing exit code"}
        return {"passed": True, "reason": "all test commands exited 0"}

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
