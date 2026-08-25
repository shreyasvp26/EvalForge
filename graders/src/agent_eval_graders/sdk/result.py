"""Structured grader result contract shared by objective and rubric families.

Graders still produce Domain ``Score`` values. This module normalizes the
``detail`` payload so runs expose a consistent, inspectable shape without a
parallel scoring subsystem.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any
from uuid import uuid4

from agent_eval_domain.common.ids import ScoreId

from agent_eval_graders.sdk.context import GradingContext
from agent_eval_graders.sdk.models import ProducedScore, make_score

DEFAULT_MAX_SCORE = 1.0


def structured_detail(
    *,
    grader: str,
    family: str,
    passed: bool | None = None,
    score: float | None = None,
    max_score: float = DEFAULT_MAX_SCORE,
    reason: str = "",
    evidence: Mapping[str, Any] | None = None,
    metadata: Mapping[str, Any] | None = None,
    duration_ms: float | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """Build the canonical Score.detail payload for a grader result."""
    detail: dict[str, Any] = {
        "grader": grader,
        "family": family,
        "passed": passed,
        "score": score,
        "max_score": max_score,
        "reason": reason,
        "evidence": dict(evidence or {}),
        "metadata": dict(metadata or {}),
    }
    if duration_ms is not None:
        detail["duration_ms"] = duration_ms
    for key, value in extra.items():
        # Preserve backward-compatible top-level keys (e.g. exit_code, missing).
        if key not in detail:
            detail[key] = value
    return detail


def produce_objective_score(
    context: GradingContext,
    *,
    grader_name: str,
    judgment: object,
    evidence_keys: Sequence[str] = (),
) -> Sequence[ProducedScore]:
    """Normalize an objective grader judgment dict into a ProducedScore."""
    data = judgment if isinstance(judgment, dict) else {}
    passed = bool(data.get("passed"))
    reason = str(data.get("reason", ""))
    numeric = data.get("numeric")
    if isinstance(numeric, (int, float)) and not isinstance(numeric, bool):
        score_value = float(numeric)
    else:
        score_value = 1.0 if passed else 0.0

    evidence: dict[str, Any] = {}
    for key in evidence_keys:
        if key in data:
            evidence[key] = data[key]
    # Capture leftover judgment keys as evidence when not already reserved.
    reserved = {"passed", "reason", "numeric", "score", "max_score"}
    for key, value in data.items():
        if key not in reserved and key not in evidence:
            evidence[key] = value

    max_score_raw = data.get("max_score", DEFAULT_MAX_SCORE)
    max_score = (
        float(max_score_raw)
        if isinstance(max_score_raw, (int, float))
        and not isinstance(max_score_raw, bool)
        else DEFAULT_MAX_SCORE
    )
    duration_raw = data.get("duration_ms")
    duration_ms = (
        float(duration_raw)
        if isinstance(duration_raw, (int, float)) and not isinstance(duration_raw, bool)
        else None
    )

    detail = structured_detail(
        grader=grader_name,
        family="objective",
        passed=passed,
        score=score_value,
        max_score=max_score,
        reason=reason,
        evidence=evidence,
        duration_ms=duration_ms,
        **{k: evidence[k] for k in evidence_keys if k in evidence},
    )
    return (
        make_score(
            score_id=ScoreId(f"score-{uuid4().hex[:12]}"),
            run_id=context.reader.metadata().run_id,
            grader_id=context.grader_id,
            grader_version_id=context.grader_version_id,
            passed=passed,
            numeric=score_value,
            reason=reason,
            detail=detail,
            metadata={"family": "objective", "grader": grader_name},
        ),
    )
