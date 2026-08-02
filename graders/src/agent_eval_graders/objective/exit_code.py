"""ExitCodeGrader — check a recorded shell command's exit code."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import uuid4

from agent_eval_domain.common.ids import ScoreId
from agent_eval_domain.execution.entities import Artifact, ExecutionEvent

from agent_eval_graders.objective._helpers import matching_shell, shell_events
from agent_eval_graders.sdk.context import GradingContext
from agent_eval_graders.sdk.grader import BaseGrader
from agent_eval_graders.sdk.models import ProducedScore, make_score


@dataclass
class ExitCodeGrader(BaseGrader):
    name: str = "exit_code"
    command_pattern: str = r"."  # match last command by default via all shells
    expected_exit_code: int = 0
    use_last_command: bool = True

    def grade(
        self,
        context: GradingContext,
        events: Sequence[ExecutionEvent],
        artifacts: Sequence[Artifact],
    ) -> object:
        del artifacts
        context.check_timeout()
        if self.use_last_command and self.command_pattern == r".":
            actions = shell_events(events)
        else:
            actions = matching_shell(events, (self.command_pattern,))
        if not actions:
            return {
                "passed": False,
                "reason": "no matching shell command in run record",
            }
        action = actions[-1]
        if action.exit_code is None:
            return {"passed": False, "reason": "matched command has no exit code"}
        passed = action.exit_code == self.expected_exit_code
        return {
            "passed": passed,
            "reason": (
                f"exit code {action.exit_code} "
                f"{'==' if passed else '!='} expected {self.expected_exit_code}"
            ),
            "exit_code": action.exit_code,
            "command": action.command,
        }

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
                detail={"grader": self.name, "exit_code": data.get("exit_code")},
            ),
        )
