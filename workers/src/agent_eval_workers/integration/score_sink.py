"""ScoreSink ← Application RecordScore (no repository access)."""

from __future__ import annotations

from dataclasses import dataclass, field

from agent_eval_application.commands.run import RecordScoreCommand
from agent_eval_application.common.actor import Actor
from agent_eval_graders.sdk.exceptions import DuplicateScoreError
from agent_eval_graders.sdk.models import ProducedScore


@dataclass
class ApplicationScoreSink:
    """Persist Grader Scores through ``RecordScore`` only."""

    record_score: object
    actor: Actor
    scores: list[ProducedScore] = field(default_factory=list)
    failures: list[tuple[str, str, str]] = field(default_factory=list)
    _versions: set[str] = field(default_factory=set)

    def on_score(self, produced: ProducedScore) -> None:
        key = produced.grader_version_id.value
        if key in self._versions:
            raise DuplicateScoreError(
                "Duplicate Score across graders for Grader Version",
                details={"grader_version_id": key},
            )
        score = produced.score
        self.record_score.execute(  # type: ignore[attr-defined]
            RecordScoreCommand(
                actor=self.actor,
                run_id=score.run_id.value,
                grader_id=score.grader_id.value,
                grader_version_id=score.grader_version_id.value,
                numeric=score.value.numeric,
                categorical=score.value.categorical,
                passed=score.value.passed,
                detail=dict(score.value.detail),
                explanation_artifact_id=(
                    score.explanation_artifact_id.value
                    if score.explanation_artifact_id is not None
                    else None
                ),
            )
        )
        self._versions.add(key)
        self.scores.append(produced)

    def on_failure(
        self,
        *,
        grader_id: str,
        grader_version_id: str,
        message: str,
    ) -> None:
        self.failures.append((grader_id, grader_version_id, message))
