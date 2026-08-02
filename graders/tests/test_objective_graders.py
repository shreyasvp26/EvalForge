"""Objective Grader Engine integration tests."""

from __future__ import annotations

import time

import pytest
from agent_eval_domain.common.ids import GraderId, GraderVersionId
from agent_eval_graders.objective import (
    BuildSuccessGrader,
    DiffValidationGrader,
    ExitCodeGrader,
    ExpectedFileGrader,
    JSONOutputGrader,
    LintGrader,
    TestPassGrader,
    default_objective_registry,
)
from agent_eval_graders.sdk import (
    DuplicateScoreError,
    GraderJudgmentError,
    GradingConfig,
    GradingContext,
    GradingOutcome,
    run_grader,
    run_graders_isolated,
)
from agent_eval_graders.sdk.execution import RecordingScoreSink
from agent_eval_graders.sdk.grader import BaseGrader
from grader_fakes import CollectingSink, InMemoryRunReader


def _ctx(
    reader: InMemoryRunReader,
    *,
    grader_id: str = "grader-1",
    version_id: str = "gv-1",
    timeout_seconds: float = 30.0,
    specification: str = "objective check",
) -> GradingContext:
    return GradingContext(
        reader=reader,
        grader_id=GraderId(grader_id),
        grader_version_id=GraderVersionId(version_id),
        grader_version_label="v1",
        grader_specification=specification,
        correlation_id="corr-1",
        config=GradingConfig(timeout_seconds=timeout_seconds),
    )


def test_build_success_deterministic() -> None:
    reader = InMemoryRunReader()
    reader.add_shell("npm run build", 0)
    sink = CollectingSink()
    result = run_grader(BuildSuccessGrader(), _ctx(reader), sink)
    assert result.outcome is GradingOutcome.SUCCEEDED
    assert sink.scores[0].value.passed is True
    # Re-run: same verdict
    sink2 = CollectingSink()
    result2 = run_grader(BuildSuccessGrader(), _ctx(reader, version_id="gv-1b"), sink2)
    assert result2.scores[0].value.passed is True


def test_build_success_failure() -> None:
    reader = InMemoryRunReader()
    reader.add_shell("npm run build", 1)
    sink = CollectingSink()
    run_grader(BuildSuccessGrader(), _ctx(reader), sink)
    assert sink.scores[0].value.passed is False


def test_exit_code_grader() -> None:
    reader = InMemoryRunReader()
    reader.add_shell("make all", 0)
    sink = CollectingSink()
    run_grader(ExitCodeGrader(expected_exit_code=0), _ctx(reader), sink)
    assert sink.scores[0].value.passed is True


def test_test_pass_and_lint() -> None:
    reader = InMemoryRunReader()
    reader.add_shell("pytest -q", 0)
    reader.add_shell("ruff check .", 0)
    assert (
        run_grader(TestPassGrader(), _ctx(reader, version_id="gv-t"), CollectingSink())
        .scores[0]
        .value.passed
        is True
    )
    assert (
        run_grader(LintGrader(), _ctx(reader, version_id="gv-l"), CollectingSink())
        .scores[0]
        .value.passed
        is True
    )


def test_expected_file_grader() -> None:
    reader = InMemoryRunReader()
    reader.add_edit("src/main.py")
    sink = CollectingSink()
    run_grader(
        ExpectedFileGrader(expected_paths=("src/main.py",)),
        _ctx(reader),
        sink,
    )
    assert sink.scores[0].value.passed is True

    sink2 = CollectingSink()
    run_grader(
        ExpectedFileGrader(expected_paths=("missing.py",)),
        _ctx(reader, version_id="gv-2"),
        sink2,
    )
    assert sink2.scores[0].value.passed is False


def test_diff_validation_forbidden_path() -> None:
    reader = InMemoryRunReader()
    reader.add_edit(".env", "secret")
    sink = CollectingSink()
    run_grader(
        DiffValidationGrader(forbidden_path_patterns=(r"^\.env$",)),
        _ctx(reader),
        sink,
    )
    assert sink.scores[0].value.passed is False


def test_json_output_grader() -> None:
    reader = InMemoryRunReader()
    reader.add_output('{"ok": true, "count": 1}')
    sink = CollectingSink()
    run_grader(
        JSONOutputGrader(required_keys=("ok", "count")),
        _ctx(reader),
        sink,
    )
    assert sink.scores[0].value.passed is True
    assert "reason" in sink.scores[0].value.detail


def test_json_output_invalid() -> None:
    reader = InMemoryRunReader()
    reader.add_output("not-json")
    sink = CollectingSink()
    run_grader(JSONOutputGrader(), _ctx(reader), sink)
    assert sink.scores[0].value.passed is False


def test_score_model_fields() -> None:
    reader = InMemoryRunReader()
    reader.add_shell("pytest", 0)
    sink = CollectingSink()
    run_grader(TestPassGrader(), _ctx(reader), sink)
    score = sink.scores[0].score
    assert score.run_id.value == "run-1"
    assert score.grader_id.value == "grader-1"
    assert score.grader_version_id.value == "gv-1"
    assert score.value.passed is True
    assert score.value.numeric == 1.0
    assert score.created_at is not None
    assert sink.scores[0].reason


def test_duplicate_score_prevention_within_invocation() -> None:
    class DupGrader(BaseGrader):
        name = "dup"

        def grade(self, context, events, artifacts):
            return {"passed": True}

        def produce_scores(self, context, judgment):
            from agent_eval_domain.common.ids import ScoreId
            from agent_eval_graders.sdk.models import make_score

            s = make_score(
                score_id=ScoreId("s1"),
                run_id=context.reader.metadata().run_id,
                grader_id=context.grader_id,
                grader_version_id=context.grader_version_id,
                passed=True,
                reason="once",
            )
            return (s, s)

    reader = InMemoryRunReader()
    sink = CollectingSink()
    with pytest.raises(DuplicateScoreError):
        run_grader(DupGrader(), _ctx(reader), sink)


def test_failure_isolation_across_graders() -> None:
    class BoomGrader(BaseGrader):
        name = "boom"

        def grade(self, context, events, artifacts):
            raise GraderJudgmentError("boom")

    reader = InMemoryRunReader()
    reader.add_shell("pytest", 0)
    reader.add_edit("a.py")

    invocations = (
        (
            "boom",
            BoomGrader(),
            _ctx(reader, grader_id="g-boom", version_id="gv-boom"),
        ),
        (
            "tests",
            TestPassGrader(),
            _ctx(reader, grader_id="g-test", version_id="gv-test"),
        ),
        (
            "files",
            ExpectedFileGrader(expected_paths=("a.py",)),
            _ctx(reader, grader_id="g-file", version_id="gv-file"),
        ),
    )
    result = run_graders_isolated(invocations)
    assert result.failed_count == 1
    assert result.succeeded_count == 2
    assert len(result.scores) == 2
    assert all(s.value.passed for s in result.scores)


def test_timeout() -> None:
    class SlowGrader(BaseGrader):
        name = "slow"

        def grade(self, context, events, artifacts):
            time.sleep(0.05)
            context.check_timeout()
            return {"passed": True}

        def produce_scores(self, context, judgment):
            from agent_eval_domain.common.ids import ScoreId
            from agent_eval_graders.sdk.models import make_score

            return (
                make_score(
                    score_id=ScoreId("s-slow"),
                    run_id=context.reader.metadata().run_id,
                    grader_id=context.grader_id,
                    grader_version_id=context.grader_version_id,
                    passed=True,
                    reason="ok",
                ),
            )

    reader = InMemoryRunReader()
    sink = CollectingSink()
    result = run_grader(
        SlowGrader(),
        _ctx(reader, timeout_seconds=0.01),
        sink,
    )
    assert result.outcome is GradingOutcome.TIMED_OUT
    assert sink.failures
    assert not sink.scores


def test_multiple_graders_registry() -> None:
    registry = default_objective_registry()
    assert "test_pass" in registry.names()
    assert "build_success" in registry.names()
    grader = registry.create("exit_code", expected_exit_code=0)
    reader = InMemoryRunReader()
    reader.add_shell("true", 0)
    sink = CollectingSink()
    run_grader(grader, _ctx(reader), sink)
    assert sink.scores[0].value.passed is True


def test_invalid_input_no_events() -> None:
    reader = InMemoryRunReader()
    sink = CollectingSink()
    run_grader(TestPassGrader(), _ctx(reader), sink)
    assert sink.scores[0].value.passed is False
    assert "no test command" in sink.scores[0].reason


def test_cross_grader_duplicate_version_prevention() -> None:
    reader = InMemoryRunReader()
    reader.add_shell("pytest", 0)
    sink = RecordingScoreSink()
    # Two graders forced to same version id — second score rejected.
    run_grader(
        TestPassGrader(),
        _ctx(reader, grader_id="g1", version_id="gv-same"),
        sink,
    )
    with pytest.raises(DuplicateScoreError):
        run_grader(
            TestPassGrader(),
            _ctx(reader, grader_id="g2", version_id="gv-same"),
            sink,
        )
