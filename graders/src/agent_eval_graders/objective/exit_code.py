"""ExitCodeGrader — check a recorded shell command's exit code."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from agent_eval_domain.execution.entities import Artifact, ExecutionEvent

from agent_eval_graders.objective._helpers import matching_shell, shell_events
from agent_eval_graders.sdk.context import GradingContext
from agent_eval_graders.sdk.grader import BaseGrader
from agent_eval_graders.sdk.models import ProducedScore
from agent_eval_graders.sdk.result import produce_objective_score


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
        return produce_objective_score(
            context,
            grader_name=self.name,
            judgment=judgment,
            evidence_keys=("exit_code", "command"),
        )
