"""Grader SDK ports — read-only Run access + score reporting."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from agent_eval_domain.execution.entities import Artifact, ExecutionEvent

from agent_eval_graders.sdk.models import GradingRunMetadata, ProducedScore


@runtime_checkable
class RunReader(Protocol):
    """Read-only view of one completed Run.

    Graders receive ONLY Execution Events, Artifacts, and Run metadata —
    never repositories, Sandbox, Adapter, or Execution Engine.
    """

    def metadata(self) -> GradingRunMetadata: ...

    def events(self) -> Sequence[ExecutionEvent]: ...

    def artifacts(self) -> Sequence[Artifact]: ...


@runtime_checkable
class ScoreSink(Protocol):
    """Reporting channel for produced Scores (Execution Engine persists)."""

    def on_score(self, produced: ProducedScore) -> None: ...

    def on_failure(
        self,
        *,
        grader_id: str,
        grader_version_id: str,
        message: str,
    ) -> None: ...
