"""ExpectedFileGrader — require recorded file edits for expected paths."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from agent_eval_domain.execution.entities import Artifact, ExecutionEvent

from agent_eval_graders.objective._helpers import file_edit_events
from agent_eval_graders.sdk.context import GradingContext
from agent_eval_graders.sdk.grader import BaseGrader
from agent_eval_graders.sdk.models import ProducedScore
from agent_eval_graders.sdk.result import produce_objective_score


@dataclass
class ExpectedFileGrader(BaseGrader):
    name: str = "expected_file"
    expected_paths: tuple[str, ...] = field(default_factory=tuple)

    def grade(
        self,
        context: GradingContext,
        events: Sequence[ExecutionEvent],
        artifacts: Sequence[Artifact],
    ) -> object:
        del artifacts
        context.check_timeout()
        if not self.expected_paths:
            return {"passed": False, "reason": "no expected_paths configured"}
        edited = {e.path for e in file_edit_events(events)}
        missing = [p for p in self.expected_paths if p not in edited]
        if missing:
            return {
                "passed": False,
                "reason": f"missing expected file edits: {missing}",
                "missing": missing,
                "edited": sorted(edited),
            }
        return {
            "passed": True,
            "reason": "all expected files were edited",
            "edited": sorted(edited),
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
            evidence_keys=("missing", "edited"),
        )
