"""Tests for optional production judge wiring."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from agent_eval_application.common.actor import Actor
from agent_eval_domain.common.ids import RunId
from agent_eval_graders.rubric import RubricGrader
from agent_eval_workers.integration.grader_resolver import PinBasedGraderResolver
from agent_eval_workers.integration.judge_wiring import (
    build_judge_provider,
    detect_judge_provider_name,
    make_rubric_factory,
)


def test_detect_judge_provider_explicit_and_disabled() -> None:
    assert detect_judge_provider_name(environ={"JUDGE_PROVIDER": "groq"}) == "groq"
    assert detect_judge_provider_name(environ={"JUDGE_PROVIDER": "none"}) is None
    assert detect_judge_provider_name(environ={}) is None


def test_detect_judge_provider_from_groq_key() -> None:
    assert detect_judge_provider_name(environ={"GROQ_API_KEY": "g"}) == "groq"
    assert detect_judge_provider_name(environ={"GRAQ_API_KEY": "g"}) == "groq"


def test_build_judge_provider_mock() -> None:
    provider = build_judge_provider(
        environ={"JUDGE_PROVIDER": "mock"},
        provider_name="mock",
    )
    assert provider is not None


def test_rubric_factory_wires_resolver() -> None:
    provider = build_judge_provider(provider_name="mock")
    assert provider is not None
    factory_builder = make_rubric_factory(provider)

    run = SimpleNamespace(pins=SimpleNamespace(grader_version_ids=["gv-rubric"]))
    graders = [
        SimpleNamespace(
            id="g1",
            name="quality",
            family="rubric",
            versions=[
                SimpleNamespace(
                    id="gv-rubric",
                    specification=json.dumps(
                        {
                            "title": "Quality",
                            "instructions": "Score carefully.",
                            "pass_threshold": 0.5,
                        }
                    ),
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
        rubric_factory=factory_builder,
    )
    specs = resolver.resolve(RunId("run-1"))
    assert len(specs) == 1
    grader = specs[0].factory()
    assert isinstance(grader, RubricGrader)


def test_rubric_factory_rejects_invalid_spec() -> None:
    provider = build_judge_provider(provider_name="mock")
    assert provider is not None
    factory_builder = make_rubric_factory(provider)
    with pytest.raises(LookupError, match="invalid specification"):
        factory_builder("quality", "{not-json", "v1")
