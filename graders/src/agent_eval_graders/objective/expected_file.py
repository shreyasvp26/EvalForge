"""ExpectedFileGrader — require recorded file edits for expected paths."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from uuid import uuid4

from agent_eval_domain.common.ids import ScoreId
from agent_eval_domain.execution.entities import Artifact, ExecutionEvent

from agent_eval_graders.objective._helpers import file_edit_events
from agent_eval_graders.sdk.context import GradingContext
from agent_eval_graders.sdk.grader import BaseGrader
from agent_eval_graders.sdk.models import ProducedScore, make_score


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
                detail={
                    "grader": self.name,
                    "missing": data.get("missing", []),
                },
            ),
        )
