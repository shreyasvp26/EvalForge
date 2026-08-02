"""JSONOutputGrader — require recorded stdout/output to contain valid JSON."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from uuid import uuid4

from agent_eval_domain.common.ids import ScoreId
from agent_eval_domain.execution.entities import Artifact, ExecutionEvent

from agent_eval_graders.objective._helpers import output_events
from agent_eval_graders.sdk.context import GradingContext
from agent_eval_graders.sdk.grader import BaseGrader
from agent_eval_graders.sdk.models import ProducedScore, make_score


@dataclass
class JSONOutputGrader(BaseGrader):
    name: str = "json_output"
    required_keys: tuple[str, ...] = field(default_factory=tuple)
    stream: str = "stdout"

    def grade(
        self,
        context: GradingContext,
        events: Sequence[ExecutionEvent],
        artifacts: Sequence[Artifact],
    ) -> object:
        del artifacts
        context.check_timeout()
        candidates = [
            o.content_summary for o in output_events(events) if o.stream == self.stream
        ]
        if not candidates:
            return {
                "passed": False,
                "reason": f"no {self.stream} output recorded",
            }

        last_error = "no valid JSON object found"
        for text in reversed(candidates):
            try:
                payload = json.loads(text)
            except json.JSONDecodeError as exc:
                last_error = str(exc)
                continue
            if not isinstance(payload, dict):
                last_error = "JSON root is not an object"
                continue
            missing = [k for k in self.required_keys if k not in payload]
            if missing:
                return {
                    "passed": False,
                    "reason": f"JSON missing required keys: {missing}",
                    "missing": missing,
                }
            return {
                "passed": True,
                "reason": "valid JSON output with required keys",
                "keys": sorted(payload.keys()),
            }
        return {"passed": False, "reason": last_error}

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
                detail={"grader": self.name, "missing": data.get("missing", [])},
            ),
        )
