"""Score aggregation policy for multi-grader Runs and Suites.

Policy (Phase 6):
- Individual objective and rubric scores remain separately visible.
- An overall numeric average is computed only when every produced score has
  a numeric value (never invented weighting).
- Pass/fail: any objective ``passed=false`` is a hard failure. An LLM judge
  cannot override a deterministic test/build/lint failure.
- If any score has ``passed=false`` (any family), the run fails.
- The run passes only when every score has ``passed=true``.
- Ambiguous when scores exist but none encode a boolean pass signal.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ScoreAggregate:
    """Deterministic rollup of one Run's scores."""

    passed: bool | None
    overall_score: float | None
    objective_failed: bool
    score_count: int
    reason: str


def _family(detail: dict[str, Any] | object) -> str:
    if isinstance(detail, dict):
        family = detail.get("family")
        if isinstance(family, str) and family.strip():
            return family.strip().lower()
    return "unknown"


def _passed(value: object) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    return None


def aggregate_scores(
    scores: Sequence[object],
) -> ScoreAggregate:
    """Aggregate ScoreDTO-like objects with passed/numeric/detail fields."""
    if not scores:
        return ScoreAggregate(
            passed=None,
            overall_score=None,
            objective_failed=False,
            score_count=0,
            reason="no scores produced",
        )

    objective_failed = False
    any_failed = False
    all_passed = True
    saw_bool = False
    numerics: list[float] = []

    for score in scores:
        value = getattr(score, "value", score)
        detail = getattr(value, "detail", {}) or {}
        family = _family(detail)
        passed = _passed(getattr(value, "passed", None))
        numeric = getattr(value, "numeric", None)
        if isinstance(numeric, (int, float)) and not isinstance(numeric, bool):
            numerics.append(float(numeric))
        if passed is False:
            saw_bool = True
            any_failed = True
            all_passed = False
            if family == "objective":
                objective_failed = True
        elif passed is True:
            saw_bool = True
        else:
            all_passed = False

    if numerics and len(numerics) == len(scores):
        overall = sum(numerics) / len(numerics)
    else:
        overall = None

    if objective_failed:
        return ScoreAggregate(
            passed=False,
            overall_score=overall,
            objective_failed=True,
            score_count=len(scores),
            reason=(
                "objective grader failure is a hard failure; "
                "judge scores cannot override it"
            ),
        )
    if any_failed:
        return ScoreAggregate(
            passed=False,
            overall_score=overall,
            objective_failed=False,
            score_count=len(scores),
            reason="one or more graders reported passed=false",
        )
    if saw_bool and all_passed:
        return ScoreAggregate(
            passed=True,
            overall_score=overall,
            objective_failed=False,
            score_count=len(scores),
            reason="all graders reported passed=true",
        )
    return ScoreAggregate(
        passed=None,
        overall_score=overall,
        objective_failed=False,
        score_count=len(scores),
        reason="scores present but pass/fail signal is incomplete",
    )
