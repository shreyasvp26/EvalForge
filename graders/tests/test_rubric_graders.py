"""Rubric Grader Engine tests — mock provider only, no external LLMs."""

from __future__ import annotations

import json

import pytest
from agent_eval_domain.common.ids import ArtifactId, GraderId, GraderVersionId, RunId
from agent_eval_domain.execution.entities import Artifact, ArtifactKind
from agent_eval_graders.objective import TestPassGrader
from agent_eval_graders.rubric import (
    DeterminismControls,
    JudgeRawResponse,
    JudgeRequest,
    MockJudgeProvider,
    RubricCriterion,
    RubricGrader,
    RubricParseError,
    RubricPromptBuilder,
    RubricSchemaError,
    RubricSpecification,
    StrictResponseParser,
    create_rubric_grader,
    default_rubric_registry,
)
from agent_eval_graders.sdk import (
    GradingConfig,
    GradingContext,
    GradingOutcome,
    run_grader,
    run_graders_isolated,
)
from grader_fakes import CollectingSink, InMemoryRunReader


def _rubric() -> RubricSpecification:
    return RubricSpecification(
        title="Code quality",
        instructions="Judge correctness and clarity of the agent's changes.",
        criteria=(
            RubricCriterion(id="correctness", description="Does the change work?"),
            RubricCriterion(id="clarity", description="Is the change readable?"),
        ),
        pass_threshold=0.7,
        scale_min=0.0,
        scale_max=1.0,
    )


def _ctx(
    reader: InMemoryRunReader,
    *,
    version_id: str = "gv-rubric-1",
    timeout_seconds: float = 30.0,
    specification: str | None = None,
) -> GradingContext:
    rubric = _rubric()
    return GradingContext(
        reader=reader,
        grader_id=GraderId("grader-rubric"),
        grader_version_id=GraderVersionId(version_id),
        grader_version_label="rubric-v1",
        grader_specification=specification or rubric.instructions,
        correlation_id="corr-rubric",
        config=GradingConfig(timeout_seconds=timeout_seconds),
    )


def _valid_response(**overrides: object) -> str:
    payload = {
        "numeric": 0.85,
        "passed": True,
        "reason": "Solid change with clear edits",
        "criteria": [
            {
                "criterion_id": "correctness",
                "score": 0.9,
                "reason": "tests implied pass",
                "passed": True,
            },
            {
                "criterion_id": "clarity",
                "score": 0.8,
                "reason": "readable diff",
                "passed": True,
            },
        ],
        "metadata": {"confidence": 0.9},
    }
    payload.update(overrides)
    return json.dumps(payload)


def test_prompt_generation_uses_only_run_record() -> None:
    reader = InMemoryRunReader()
    reader.add_edit("src/app.py", "@@\n-old\n+new\n")
    reader.add_shell("pytest", 0)
    reader._artifacts.append(
        Artifact(
            id=ArtifactId("art-1"),
            run_id=RunId("run-1"),
            kind=ArtifactKind.DIFF,
            storage_key="runs/run-1/diff.patch",
            content_type="text/plain",
            size_bytes=12,
            checksum="abc",
        )
    )
    rubric = _rubric()
    ctx = _ctx(reader)
    prompt = RubricPromptBuilder().build(
        context=ctx,
        events=reader.events(),
        artifacts=reader.artifacts(),
        rubric=rubric,
    )
    assert prompt.grader_version_id == "gv-rubric-1"
    assert prompt.rubric_fingerprint == rubric.fingerprint()
    assert "Code quality" in prompt.user
    assert "src/app.py" in prompt.user
    assert "pytest" in prompt.user
    assert "runs/run-1/diff.patch" in prompt.user
    assert "agent-v1" in prompt.user
    # Must not invent other runs / scores / external context.
    assert "other run" not in prompt.user.lower()
    assert "score_id" not in prompt.user.lower()
    assert "untrusted DATA" in prompt.system


def test_prompt_deterministic_for_same_inputs() -> None:
    reader = InMemoryRunReader()
    reader.add_output('{"ok": true}')
    rubric = _rubric()
    ctx = _ctx(reader)
    builder = RubricPromptBuilder()
    a = builder.build(
        context=ctx,
        events=reader.events(),
        artifacts=reader.artifacts(),
        rubric=rubric,
    )
    b = builder.build(
        context=ctx,
        events=reader.events(),
        artifacts=reader.artifacts(),
        rubric=rubric,
    )
    assert a.system == b.system
    assert a.user == b.user
    assert a.rubric_fingerprint == b.rubric_fingerprint


def test_response_parsing_success() -> None:
    parser = StrictResponseParser()
    judgment = parser.parse(
        JudgeRawResponse(content=_valid_response(), model="mock"),
        rubric=_rubric(),
        controls=DeterminismControls(),
    )
    assert judgment.passed is True
    assert judgment.numeric == 0.85
    assert len(judgment.criteria) == 2
    assert "Solid change" in judgment.reason


def test_invalid_json_is_parse_failure() -> None:
    parser = StrictResponseParser()
    with pytest.raises(RubricParseError):
        parser.parse(
            JudgeRawResponse(content="not-json", model="mock"),
            rubric=_rubric(),
            controls=DeterminismControls(),
        )


def test_schema_failure_missing_reason() -> None:
    parser = StrictResponseParser()
    with pytest.raises(RubricSchemaError):
        parser.parse(
            JudgeRawResponse(
                content='{"numeric": 0.5, "passed": false}',
                model="mock",
            ),
            rubric=_rubric(),
            controls=DeterminismControls(),
        )


def test_schema_failure_unknown_criterion() -> None:
    parser = StrictResponseParser()
    with pytest.raises(RubricSchemaError):
        parser.parse(
            JudgeRawResponse(
                content=_valid_response(
                    criteria=[
                        {
                            "criterion_id": "unknown",
                            "score": 1.0,
                            "reason": "x",
                        }
                    ]
                ),
                model="mock",
            ),
            rubric=_rubric(),
            controls=DeterminismControls(),
        )


def test_schema_failure_out_of_scale() -> None:
    parser = StrictResponseParser()
    with pytest.raises(RubricSchemaError):
        parser.parse(
            JudgeRawResponse(
                content=_valid_response(numeric=9.0),
                model="mock",
            ),
            rubric=_rubric(),
            controls=DeterminismControls(),
        )


def test_score_production_via_run_grader() -> None:
    reader = InMemoryRunReader()
    reader.add_edit("main.py")
    provider = MockJudgeProvider(response=_valid_response())
    grader = RubricGrader(rubric=_rubric(), provider=provider)
    sink = CollectingSink()
    result = run_grader(grader, _ctx(reader), sink)
    assert result.outcome is GradingOutcome.SUCCEEDED
    assert sink.scores[0].value.passed is True
    assert sink.scores[0].value.numeric == 0.85
    assert sink.scores[0].reason
    assert sink.scores[0].metadata["family"] == "rubric"
    assert "criteria" in sink.scores[0].value.detail
    assert provider.call_count == 1


def test_judge_timeout() -> None:
    reader = InMemoryRunReader()
    provider = MockJudgeProvider(simulate_timeout=True)
    grader = RubricGrader(rubric=_rubric(), provider=provider)
    sink = CollectingSink()
    result = run_grader(grader, _ctx(reader), sink)
    assert result.outcome is GradingOutcome.TIMED_OUT
    assert sink.failures
    assert not sink.scores


def test_provider_unavailable_is_retryable_failure() -> None:
    reader = InMemoryRunReader()
    provider = MockJudgeProvider(simulate_unavailable=True)
    grader = RubricGrader(rubric=_rubric(), provider=provider)
    sink = CollectingSink()
    result = run_grader(grader, _ctx(reader), sink)
    assert result.outcome is GradingOutcome.FAILED
    assert sink.failures
    assert "unavailable" in sink.failures[0][2].lower()


def test_invalid_response_grades_as_failure() -> None:
    reader = InMemoryRunReader()
    provider = MockJudgeProvider(response="{bad")
    grader = RubricGrader(rubric=_rubric(), provider=provider)
    sink = CollectingSink()
    result = run_grader(grader, _ctx(reader), sink)
    assert result.outcome is GradingOutcome.FAILED
    assert not sink.scores


def test_partial_grading_isolation_with_objective_sibling() -> None:
    reader = InMemoryRunReader()
    reader.add_shell("pytest", 0)
    reader.add_edit("a.py")

    boom = RubricGrader(
        rubric=_rubric(),
        provider=MockJudgeProvider(simulate_unavailable=True),
        name="rubric-boom",
    )
    ok = RubricGrader(
        rubric=_rubric(),
        provider=MockJudgeProvider(response=_valid_response()),
        name="rubric-ok",
    )
    objective = TestPassGrader()

    result = run_graders_isolated(
        (
            ("boom", boom, _ctx(reader, version_id="gv-boom")),
            ("ok", ok, _ctx(reader, version_id="gv-ok")),
            (
                "tests",
                objective,
                GradingContext(
                    reader=reader,
                    grader_id=GraderId("g-test"),
                    grader_version_id=GraderVersionId("gv-test"),
                    grader_version_label="v1",
                    grader_specification="tests",
                    correlation_id="corr",
                ),
            ),
        )
    )
    assert result.failed_count == 1
    assert result.succeeded_count == 2
    assert len(result.scores) == 2


def test_determinism_controls_passed_to_provider() -> None:
    seen: list[JudgeRequest] = []

    def handler(request: JudgeRequest) -> JudgeRawResponse:
        seen.append(request)
        return JudgeRawResponse(content=_valid_response(), model="mock")

    reader = InMemoryRunReader()
    controls = DeterminismControls(temperature=0.0, seed=42, model_hint="mock-v1")
    grader = RubricGrader(
        rubric=_rubric(),
        provider=MockJudgeProvider(handler=handler),
        controls=controls,
    )
    run_grader(grader, _ctx(reader), CollectingSink())
    assert seen[0].controls.temperature == 0.0
    assert seen[0].controls.seed == 42
    assert seen[0].controls.model_hint == "mock-v1"
    sink = CollectingSink()
    run_grader(grader, _ctx(reader, version_id="gv-2"), sink)
    assert sink.scores[0].value.detail["determinism"]["seed"] == 42


def test_rubric_fingerprint_stable_and_version_bound() -> None:
    a = _rubric()
    b = _rubric()
    assert a.fingerprint() == b.fingerprint()
    changed = RubricSpecification(
        title=a.title,
        instructions=a.instructions + " (revised)",
        criteria=a.criteria,
        pass_threshold=a.pass_threshold,
    )
    assert changed.fingerprint() != a.fingerprint()


def test_registry_and_factory() -> None:
    registry = default_rubric_registry()
    assert "rubric" in registry.names()
    grader = create_rubric_grader(
        rubric=_rubric(),
        provider=MockJudgeProvider(response=_valid_response()),
    )
    reader = InMemoryRunReader()
    result = run_grader(grader, _ctx(reader), CollectingSink())
    assert result.outcome is GradingOutcome.SUCCEEDED


def test_pass_threshold_derives_passed() -> None:
    parser = StrictResponseParser()
    judgment = parser.parse(
        JudgeRawResponse(
            content=json.dumps({"numeric": 0.75, "reason": "above threshold"}),
            model="mock",
        ),
        rubric=_rubric(),
        controls=DeterminismControls(),
    )
    assert judgment.passed is True


def test_context_timeout_during_slow_judge() -> None:
    reader = InMemoryRunReader()
    provider = MockJudgeProvider(
        response=_valid_response(),
        sleep_seconds=0.05,
    )
    grader = RubricGrader(rubric=_rubric(), provider=provider)
    sink = CollectingSink()
    result = run_grader(
        grader,
        _ctx(reader, timeout_seconds=0.01),
        sink,
    )
    assert result.outcome is GradingOutcome.TIMED_OUT
    assert not sink.scores
