"""DiffValidationGrader — validate recorded file edits against path rules."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field

from agent_eval_domain.execution.entities import Artifact, ExecutionEvent

from agent_eval_graders.objective._helpers import file_edit_events
from agent_eval_graders.sdk.context import GradingContext
from agent_eval_graders.sdk.grader import BaseGrader
from agent_eval_graders.sdk.models import ProducedScore
from agent_eval_graders.sdk.result import produce_objective_score


@dataclass
class DiffValidationGrader(BaseGrader):
    """Require at least one file edit; optionally constrain allowed/forbidden paths."""

    name: str = "diff_validation"
    require_edits: bool = True
    allowed_path_patterns: tuple[str, ...] = field(default_factory=tuple)
    forbidden_path_patterns: tuple[str, ...] = field(default_factory=tuple)
    require_nonempty_diff: bool = True

    def grade(
        self,
        context: GradingContext,
        events: Sequence[ExecutionEvent],
        artifacts: Sequence[Artifact],
    ) -> object:
        del artifacts
        context.check_timeout()
        edits = file_edit_events(events)
        if self.require_edits and not edits:
            return {"passed": False, "reason": "no file edits recorded"}

        if self.require_nonempty_diff:
            empty = [e.path for e in edits if not e.diff_summary.strip()]
            if empty:
                return {
                    "passed": False,
                    "reason": f"empty diffs for paths: {empty}",
                }

        allowed = [re.compile(p) for p in self.allowed_path_patterns]
        forbidden = [re.compile(p) for p in self.forbidden_path_patterns]

        for edit in edits:
            if forbidden and any(rx.search(edit.path) for rx in forbidden):
                return {
                    "passed": False,
                    "reason": f"forbidden path edited: {edit.path}",
                }
            if allowed and not any(rx.search(edit.path) for rx in allowed):
                return {
                    "passed": False,
                    "reason": f"path not in allowed set: {edit.path}",
                }

        return {
            "passed": True,
            "reason": f"validated {len(edits)} file edit(s)",
            "edit_count": len(edits),
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
            evidence_keys=("edit_count",),
        )
