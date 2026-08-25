"""Score aggregation policy tests."""

from __future__ import annotations

from types import SimpleNamespace

from agent_eval_application.scoring import aggregate_scores


def _score(*, passed: bool | None, numeric: float | None, family: str):
    return SimpleNamespace(
        value=SimpleNamespace(
            passed=passed,
            numeric=numeric,
            detail={"family": family},
        )
    )


def test_objective_failure_is_hard_fail_even_with_passing_judge() -> None:
    agg = aggregate_scores(
        [
            _score(passed=False, numeric=0.0, family="objective"),
            _score(passed=True, numeric=0.95, family="rubric"),
        ]
    )
    assert agg.passed is False
    assert agg.objective_failed is True
    assert "hard failure" in agg.reason


def test_all_passed_yields_pass_and_average() -> None:
    agg = aggregate_scores(
        [
            _score(passed=True, numeric=1.0, family="objective"),
            _score(passed=True, numeric=0.8, family="rubric"),
        ]
    )
    assert agg.passed is True
    assert agg.overall_score == 0.9


def test_empty_scores_are_ambiguous() -> None:
    agg = aggregate_scores([])
    assert agg.passed is None
    assert agg.score_count == 0
