"""Grader contract — measurement boundary only."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from agent_eval_domain.execution.entities import Artifact, ExecutionEvent

from agent_eval_graders.sdk.context import GradingContext
from agent_eval_graders.sdk.models import ProducedScore


@runtime_checkable
class Grader(Protocol):
    """Uniform Grader contract (Grader Architecture — Grader Contract).

    Lifecycle: initialize → read_run → grade → produce_scores → cleanup.
    Invocations are stateless and isolated.
    """

    @property
    def name(self) -> str: ...

    def initialize(self, context: GradingContext) -> None: ...

    def read_run(
        self,
        context: GradingContext,
    ) -> tuple[Sequence[ExecutionEvent], Sequence[Artifact]]:
        """Consume the Run record needed for judgment."""
        ...

    def grade(
        self,
        context: GradingContext,
        events: Sequence[ExecutionEvent],
        artifacts: Sequence[Artifact],
    ) -> object:
        """Apply deterministic judgment; return opaque judgment state."""
        ...

    def produce_scores(
        self,
        context: GradingContext,
        judgment: object,
    ) -> Sequence[ProducedScore]:
        """Materialize immutable Domain Scores from judgment."""
        ...

    def cleanup(self, context: GradingContext) -> None: ...


class BaseGrader:
    """Optional base with default read_run / cleanup."""

    name: str = "base"

    def initialize(self, context: GradingContext) -> None:
        del context

    def read_run(
        self,
        context: GradingContext,
    ) -> tuple[Sequence[ExecutionEvent], Sequence[Artifact]]:
        return context.reader.events(), context.reader.artifacts()

    def grade(
        self,
        context: GradingContext,
        events: Sequence[ExecutionEvent],
        artifacts: Sequence[Artifact],
    ) -> object:
        del context, events, artifacts
        return None

    def produce_scores(
        self,
        context: GradingContext,
        judgment: object,
    ) -> Sequence[ProducedScore]:
        del context, judgment
        return ()

    def cleanup(self, context: GradingContext) -> None:
        del context
