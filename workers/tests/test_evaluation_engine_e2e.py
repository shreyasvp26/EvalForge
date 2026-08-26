"""Phase 6 evaluation-engine end-to-end tests (deterministic path)."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from agent_eval_application.commands.grader import (
    CreateGraderCommand,
    CreateGraderDraftVersionCommand,
    PublishGraderVersionCommand,
)
from agent_eval_application.commands.run import CreateRunCommand
from agent_eval_application.common.actor import Actor
from agent_eval_application.queries.queries import GetRunProvenanceQuery, GetRunQuery
from agent_eval_application.scoring import aggregate_scores
from agent_eval_application.use_cases.grader import (
    CreateGrader,
    CreateGraderDraftVersion,
    ListGraders,
    PublishGraderVersion,
)
from agent_eval_application.use_cases.provenance import GetRunProvenance
from agent_eval_application.use_cases.run import CreateRun, GetRun
from agent_eval_domain.common.ids import RunId
from agent_eval_graders.objective import ExpectedFileGrader
from agent_eval_graders.rubric import (
    DeterminismControls,
    JudgeRawResponse,
    MockJudgeProvider,
    RubricCriterion,
    RubricGrader,
    RubricSpecification,
    StrictResponseParser,
)
from agent_eval_graders.rubric.exceptions import RubricParseError, RubricSchemaError
from agent_eval_workers.execution_engine import EngineOutcomeKind
from agent_eval_workers.integration.composition import build_production_harness
from agent_eval_workers.integration.grader_resolver import PinBasedGraderResolver
from agent_eval_workers.integration.grading_scheduler import GraderInvocationSpec
from agent_eval_workers.integration.judge_wiring import make_rubric_factory
from agent_eval_workers.integration.process import build_production_worker
from agent_eval_workers.worker.memory_queue import InMemoryWorkerQueue
from docker_fakes import FakeDockerEngine

pytest_plugins = ["test_run_use_cases"]


def _create_run(world, *, grader_refs, platform_version_id=None):
    platform_version_id = platform_version_id or world["platform_version_id"]
    return CreateRun(
        world["uow"],
        world["ids"],
        world["auth"],
        world["events"],
        world["queue"],
        world["idempotency"],
    ).execute(
        CreateRunCommand(
            actor=world["actor"],
            project_id=world["project_id"],
            case_id=world["case_id"],
            case_version_id=world["case_version_id"],
            prompt_version_id=world["prompt_version_id"],
            agent_id=world["agent_id"],
            agent_version_id=world["agent_version_id"],
            adapter_version_id=world["adapter_version_id"],
            grader_version_refs=tuple(grader_refs),
            platform_version_id=platform_version_id,
        )
    )


def test_deterministic_benchmark_produces_structured_scores(world) -> None:
    """CreateRun → worker → objective grade → structured Score.detail + provenance."""
    run = _create_run(
        world,
        grader_refs=((world["grader_id"], world["grader_version_id"]),),
    )
    queue = InMemoryWorkerQueue()
    queue.enqueue(RunId(run.id))
    bundle = build_production_worker(
        queue=queue,
        uow_factory=world["uow"],
        ids=world["ids"],
        events=world["events"],
        docker_engine=FakeDockerEngine(),
        actor=world["actor"],
        auth=world["auth"],
        adapter_mode="deterministic",
        sandbox_mode="fake",
    )
    outcome = bundle.worker.run_once(block=False)
    assert outcome is not None
    assert outcome.kind is EngineOutcomeKind.COMPLETED

    finished = GetRun(world["uow"], world["auth"]).execute(
        GetRunQuery(actor=world["actor"], run_id=run.id)
    )
    assert finished.status == "completed"
    assert finished.produced_score_count >= 1
    detail = finished.scores[0].value.detail
    assert detail.get("family") == "objective"
    assert "score" in detail

    provenance = GetRunProvenance(world["uow"], world["auth"]).execute(
        GetRunProvenanceQuery(actor=world["actor"], run_id=run.id)
    )
    assert provenance.commit_sha == "deadbeef"
    assert provenance.adapter_key == "claude_code"
    assert provenance.platform_version_id == world["platform_version_id"]
    agg = aggregate_scores(finished.scores)
    assert agg.score_count == finished.produced_score_count


def test_rubric_pin_fails_closed_without_judge(world) -> None:
    run = SimpleNamespace(
        pins=SimpleNamespace(grader_version_ids=["gv-rubric"]),
    )
    graders = [
        SimpleNamespace(
            id="g-rubric",
            name="quality",
            family="rubric",
            versions=[
                SimpleNamespace(
                    id="gv-rubric",
                    specification='{"title":"Q","instructions":"Score"}',
                    label="v1",
                )
            ],
        )
    ]

    class _GetRun:
        def execute(self, _q):
            return run

    class _ListGraders:
        def execute(self, _q):
            return graders

    resolver = PinBasedGraderResolver(
        actor=Actor(id="system"),
        get_run=_GetRun(),
        list_graders=_ListGraders(),
    )
    with pytest.raises(LookupError, match="requires a configured judge provider"):
        resolver.resolve(RunId("run-1"))


def test_rubric_and_objective_execute_with_mock_judge(world) -> None:
    # Publish additional versions of the case-declared grader so rubric can pin.
    refs: list[tuple[str, str]] = [(world["grader_id"], world["grader_version_id"])]
    for label in ("v-rubric",):
        gv = CreateGraderDraftVersion(
            world["uow"], world["ids"], world["auth"], world["events"]
        ).execute(
            CreateGraderDraftVersionCommand(
                actor=world["actor"],
                grader_id=world["grader_id"],
                label=label,
                specification=label,
            )
        )
        gv = PublishGraderVersion(world["uow"], world["auth"], world["events"]).execute(
            PublishGraderVersionCommand(
                actor=world["actor"],
                grader_id=world["grader_id"],
                version_id=gv.id,
            )
        )
        refs.append((world["grader_id"], gv.id))

    judge_body = json.dumps(
        {
            "passed": True,
            "score": 0.9,
            "reason": "Looks correct",
            "criteria": [
                {
                    "criterion_id": "correctness",
                    "score": 0.9,
                    "reason": "ok",
                    "passed": True,
                }
            ],
        }
    )
    rubric = RubricSpecification(
        title="Quality",
        instructions="Score carefully.",
        criteria=(RubricCriterion(id="correctness", description="Does it work?"),),
        pass_threshold=0.5,
    )
    files_id, files_vid = refs[0]
    rubric_id, rubric_vid = refs[1]

    specs = (
        GraderInvocationSpec(
            name="expected_file",
            grader_id=files_id,
            grader_version_id=files_vid,
            factory=lambda: ExpectedFileGrader(expected_paths=("main.py",)),
            specification="main.py",
        ),
        GraderInvocationSpec(
            name="quality",
            grader_id=rubric_id,
            grader_version_id=rubric_vid,
            factory=lambda: RubricGrader(
                rubric=rubric,
                provider=MockJudgeProvider(response=judge_body),
                name="quality",
            ),
            specification=rubric.instructions,
        ),
    )
    run = _create_run(world, grader_refs=tuple(refs))
    harness = build_production_harness(
        uow_factory=world["uow"],
        ids=world["ids"],
        events=world["events"],
        auth=world["auth"],
        actor=world["actor"],
        docker_engine=FakeDockerEngine(),
        grader_specs=specs,
        judge_response=judge_body,
    )
    harness.enqueue(run.id)
    outcome = harness.worker.run_once(block=False)
    assert outcome is not None
    assert outcome.kind is EngineOutcomeKind.COMPLETED
    finished = GetRun(world["uow"], world["auth"]).execute(
        GetRunQuery(actor=world["actor"], run_id=run.id)
    )
    assert finished.status == "completed"
    families = {s.value.detail.get("family") for s in finished.scores}
    assert "objective" in families
    assert "rubric" in families
    agg = aggregate_scores(finished.scores)
    assert agg.passed is True


def test_malformed_judge_response_fails_grader_not_silently() -> None:
    parser = StrictResponseParser()
    rubric = RubricSpecification(title="t", instructions="i", pass_threshold=0.5)
    with pytest.raises((RubricParseError, RubricSchemaError)):
        parser.parse(
            JudgeRawResponse(content="not json at all", model="mock"),
            rubric=rubric,
            controls=DeterminismControls(),
        )
    with pytest.raises(RubricSchemaError):
        parser.parse(
            JudgeRawResponse(
                content='{"passed": true}',
                model="mock",
            ),
            rubric=rubric,
            controls=DeterminismControls(),
        )


def test_rubric_factory_parses_specification(world) -> None:
    """Published rubric grader versions resolve through judge wiring."""
    rubric = CreateGrader(
        world["uow"], world["ids"], world["auth"], world["events"]
    ).execute(
        CreateGraderCommand(actor=world["actor"], name="wired-rubric", family="rubric")
    )
    gv = CreateGraderDraftVersion(
        world["uow"], world["ids"], world["auth"], world["events"]
    ).execute(
        CreateGraderDraftVersionCommand(
            actor=world["actor"],
            grader_id=rubric.id,
            label="v1",
            specification=json.dumps(
                {
                    "title": "Quality",
                    "instructions": "Score carefully.",
                    "pass_threshold": 0.5,
                }
            ),
        )
    )
    gv = PublishGraderVersion(world["uow"], world["auth"], world["events"]).execute(
        PublishGraderVersionCommand(
            actor=world["actor"], grader_id=rubric.id, version_id=gv.id
        )
    )
    # Bypass Case applicability by resolving against a synthetic Run pin list.
    synthetic = SimpleNamespace(pins=SimpleNamespace(grader_version_ids=[gv.id]))

    class _GetRun:
        def execute(self, _q):
            return synthetic

    resolver = PinBasedGraderResolver(
        actor=world["actor"],
        get_run=_GetRun(),
        list_graders=ListGraders(world["uow"], world["auth"]),
        rubric_factory=make_rubric_factory(MockJudgeProvider()),
    )
    specs = resolver.resolve(RunId("run-synthetic"))
    assert len(specs) == 1
    assert isinstance(specs[0].factory(), RubricGrader)
