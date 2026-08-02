"""Rubric ports — injectable judge provider and prompt builder."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from agent_eval_domain.execution.entities import Artifact, ExecutionEvent

from agent_eval_graders.rubric.models import (
    DeterminismControls,
    JudgePrompt,
    JudgeRawResponse,
    JudgeRequest,
    ParsedJudgment,
    RubricSpecification,
)
from agent_eval_graders.sdk.context import GradingContext


@runtime_checkable
class JudgeProvider(Protocol):
    """Injectable LLM-as-judge provider — no vendor coupling in the SDK."""

    def complete(self, request: JudgeRequest) -> JudgeRawResponse:
        """Invoke the judge model. Must not call repositories or mutate Runs."""
        ...


@runtime_checkable
class PromptBuilder(Protocol):
    """Build a judge prompt from Run record + pinned rubric only."""

    def build(
        self,
        *,
        context: GradingContext,
        events: Sequence[ExecutionEvent],
        artifacts: Sequence[Artifact],
        rubric: RubricSpecification,
    ) -> JudgePrompt: ...


@runtime_checkable
class ResponseParser(Protocol):
    """Strictly parse and validate a judge response."""

    def parse(
        self,
        raw: JudgeRawResponse,
        *,
        rubric: RubricSpecification,
        controls: DeterminismControls,
    ) -> ParsedJudgment: ...
