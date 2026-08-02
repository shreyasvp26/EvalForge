"""Immutable GradingContext for one Grader invocation."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import monotonic

from agent_eval_domain.common.ids import GraderId, GraderVersionId

from agent_eval_graders.sdk.exceptions import GraderTimeoutError
from agent_eval_graders.sdk.ports import RunReader


@dataclass(frozen=True, slots=True)
class GradingConfig:
    timeout_seconds: float = 60.0


@dataclass(frozen=True, slots=True)
class GradingContext:
    """Everything a Grader needs for one isolated invocation.

    Immutable after creation. Holds pinned Grader Version identity and a
    read-only RunReader — never Sandbox / Adapter / Engine references.
    """

    reader: RunReader
    grader_id: GraderId
    grader_version_id: GraderVersionId
    grader_version_label: str
    grader_specification: str
    correlation_id: str
    config: GradingConfig = field(default_factory=GradingConfig)
    _started_at: float = field(default_factory=monotonic)

    def check_timeout(self) -> None:
        elapsed = monotonic() - self._started_at
        if elapsed > self.config.timeout_seconds:
            raise GraderTimeoutError(
                f"Grader {self.grader_id.value} exceeded timeout",
                details={
                    "grader_id": self.grader_id.value,
                    "grader_version_id": self.grader_version_id.value,
                    "elapsed_seconds": elapsed,
                    "timeout_seconds": self.config.timeout_seconds,
                },
            )
