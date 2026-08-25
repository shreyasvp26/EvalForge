"""Tests for structured grader result contract and rubric specification parsing."""

from __future__ import annotations

import json

import pytest
from agent_eval_domain.common.ids import GraderId, GraderVersionId
from agent_eval_graders.objective import ExitCodeGrader
from agent_eval_graders.rubric import (
    DeterminismControls,
    JudgeRawResponse,
    RubricCriterion,
    RubricSpecification,
    StrictResponseParser,
    parse_rubric_specification,
)
from agent_eval_graders.sdk import (
    GradingConfig,
    GradingContext,
    run_grader,
    structured_detail,
)
from grader_fakes import CollectingSink, InMemoryRunReader


def test_structured_detail_shape() -> None:
    detail = structured_detail(
        grader="test_pass",
        family="objective",
        passed=True,
        score=1.0,
        max_score=1.0,
        reason="ok",
        evidence={"exit_code": 0},
        duration_ms=12.5,
    )
    assert detail["family"] == "objective"
    assert detail["score"] == 1.0
    assert detail["max_score"] == 1.0
    assert detail["evidence"]["exit_code"] == 0
    assert detail["duration_ms"] == 12.5


def test_objective_score_includes_structured_detail() -> None:
    reader = InMemoryRunReader()
    reader.add_shell("make all", 0)
    sink = CollectingSink()
    run_grader(
        ExitCodeGrader(expected_exit_code=0),
        GradingContext(
            reader=reader,
            grader_id=GraderId("g1"),
            grader_version_id=GraderVersionId("gv1"),
            grader_version_label="v1",
            grader_specification="exit",
            correlation_id="c1",
            config=GradingConfig(timeout_seconds=30.0),
        ),
        sink,
    )
    detail = sink.scores[0].value.detail
    assert detail["family"] == "objective"
    assert detail["grader"] == "exit_code"
    assert detail["passed"] is True
    assert detail["score"] == 1.0
    assert "exit_code" in detail["evidence"]


def test_parse_rubric_specification_json() -> None:
    raw = json.dumps(
        {
            "title": "Quality",
            "instructions": "Judge correctness.",
            "criteria": [
                {"id": "correctness", "description": "Does it work?", "weight": 1.0}
            ],
            "pass_threshold": 0.6,
        }
    )
    rubric = parse_rubric_specification(raw)
    assert rubric.title == "Quality"
    assert rubric.pass_threshold == 0.6
    assert rubric.criteria[0].id == "correctness"


def test_parse_rubric_specification_freeform() -> None:
    rubric = parse_rubric_specification(
        "Score requirement adherence carefully.",
        default_title="adhoc",
    )
    assert rubric.title == "adhoc"
    assert "requirement adherence" in rubric.instructions


def test_parse_rubric_specification_rejects_empty() -> None:
    with pytest.raises(ValueError, match="empty"):
        parse_rubric_specification("   ")


def test_judge_parser_accepts_score_and_name_aliases() -> None:
    parser = StrictResponseParser()
    rubric = RubricSpecification(
        title="t",
        instructions="i",
        criteria=(RubricCriterion(id="requirement_adherence", description="req"),),
        pass_threshold=0.5,
    )
    raw = JudgeRawResponse(
        content=json.dumps(
            {
                "passed": True,
                "score": 0.85,
                "reason": "Meets requirements",
                "criteria": [
                    {
                        "name": "requirement_adherence",
                        "score": 0.9,
                        "reason": "ok",
                    }
                ],
            }
        ),
        model="mock",
    )
    parsed = parser.parse(raw, rubric=rubric, controls=DeterminismControls())
    assert parsed.numeric == 0.85
    assert parsed.passed is True
    assert parsed.criteria[0].criterion_id == "requirement_adherence"
