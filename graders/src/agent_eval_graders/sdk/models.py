"""Grader SDK value objects."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from agent_eval_domain.common.events import utc_now
from agent_eval_domain.common.ids import (
    ArtifactId,
    GraderId,
    GraderVersionId,
    RunId,
    ScoreId,
)
from agent_eval_domain.execution.entities import Score, ScoreValue


class GradingOutcome(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TIMED_OUT = "timed_out"


@dataclass(frozen=True, slots=True)
class GradingRunMetadata:
    """Run facts a Grader may read — never live Sandbox / Adapter state."""

    run_id: RunId
    agent_version_id: str
    adapter_version_id: str
    case_version_id: str
    prompt_version_id: str
    status: str = "grading"


@dataclass(frozen=True, slots=True)
class ProducedScore:
    """Immutable Score ready for the Execution Engine to persist."""

    score: Score
    reason: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def grader_version_id(self) -> GraderVersionId:
        return self.score.grader_version_id

    @property
    def value(self) -> ScoreValue:
        return self.score.value


def make_score(
    *,
    score_id: ScoreId,
    run_id: RunId,
    grader_id: GraderId,
    grader_version_id: GraderVersionId,
    passed: bool | None = None,
    numeric: float | None = None,
    categorical: str | None = None,
    reason: str = "",
    detail: Mapping[str, Any] | None = None,
    created_at: datetime | None = None,
    explanation_artifact_id: ArtifactId | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> ProducedScore:
    """Build a Domain Score + supporting reason/metadata."""
    detail_dict: dict[str, Any] = dict(detail or {})
    if reason:
        detail_dict.setdefault("reason", reason)
    value = ScoreValue(
        numeric=numeric,
        categorical=categorical,
        passed=passed,
        detail=detail_dict,
    )
    score = Score(
        id=score_id,
        run_id=run_id,
        grader_id=grader_id,
        grader_version_id=grader_version_id,
        value=value,
        created_at=created_at or utc_now(),
        explanation_artifact_id=explanation_artifact_id,
    )
    return ProducedScore(
        score=score,
        reason=reason,
        metadata=dict(metadata or {}),
    )
