"""Grader lifecycle driver."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from agent_eval_graders.sdk.context import GradingContext
from agent_eval_graders.sdk.exceptions import (
    DuplicateScoreError,
    GraderError,
    GraderInitializationError,
    GraderTimeoutError,
)
from agent_eval_graders.sdk.grader import Grader
from agent_eval_graders.sdk.models import GradingOutcome, ProducedScore
from agent_eval_graders.sdk.ports import ScoreSink


class GraderPhase(StrEnum):
    UNINITIALIZED = "uninitialized"
    INITIALIZED = "initialized"
    READING = "reading"
    GRADING = "grading"
    PRODUCING = "producing"
    FINISHED = "finished"
    CLEANED_UP = "cleaned_up"
    FAILED = "failed"


@dataclass
class LifecycleDriver:
    """Drives initialize → read_run → grade → produce_scores → cleanup."""

    grader: Grader
    sink: ScoreSink
    phase: GraderPhase = GraderPhase.UNINITIALIZED
    outcome: GradingOutcome | None = None
    scores: list[ProducedScore] = field(default_factory=list)
    _seen_versions: set[str] = field(default_factory=set)

    def run(self, context: GradingContext) -> GradingOutcome:
        try:
            self._initialize(context)
            events, artifacts = self._read(context)
            judgment = self._grade(context, events, artifacts)
            self._produce(context, judgment)
            self.outcome = GradingOutcome.SUCCEEDED
            self.phase = GraderPhase.FINISHED
            return GradingOutcome.SUCCEEDED
        except GraderTimeoutError as exc:
            self.outcome = GradingOutcome.TIMED_OUT
            self.phase = GraderPhase.FAILED
            self.sink.on_failure(
                grader_id=context.grader_id.value,
                grader_version_id=context.grader_version_id.value,
                message=str(exc),
            )
            return GradingOutcome.TIMED_OUT
        except DuplicateScoreError:
            self.outcome = GradingOutcome.FAILED
            self.phase = GraderPhase.FAILED
            raise
        except GraderError as exc:
            # Judgment / init failures are classified and contained — never raised
            # to sibling graders (Isolation Between Graders).
            self.outcome = GradingOutcome.FAILED
            self.phase = GraderPhase.FAILED
            self.sink.on_failure(
                grader_id=context.grader_id.value,
                grader_version_id=context.grader_version_id.value,
                message=str(exc),
            )
            return GradingOutcome.FAILED
        except Exception as exc:  # noqa: BLE001
            self.outcome = GradingOutcome.FAILED
            self.phase = GraderPhase.FAILED
            self.sink.on_failure(
                grader_id=context.grader_id.value,
                grader_version_id=context.grader_version_id.value,
                message=str(exc),
            )
            return GradingOutcome.FAILED
        finally:
            self._cleanup(context)

    def _initialize(self, context: GradingContext) -> None:
        context.check_timeout()
        try:
            self.grader.initialize(context)
        except GraderError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise GraderInitializationError(
                f"Grader initialize failed: {exc}",
                cause=exc,
            ) from exc
        self.phase = GraderPhase.INITIALIZED

    def _read(self, context: GradingContext):
        context.check_timeout()
        self.phase = GraderPhase.READING
        return self.grader.read_run(context)

    def _grade(self, context: GradingContext, events, artifacts):
        context.check_timeout()
        self.phase = GraderPhase.GRADING
        return self.grader.grade(context, events, artifacts)

    def _produce(self, context: GradingContext, judgment: object) -> None:
        context.check_timeout()
        self.phase = GraderPhase.PRODUCING
        produced = self.grader.produce_scores(context, judgment)
        for item in produced:
            version_key = item.grader_version_id.value
            if version_key in self._seen_versions:
                raise DuplicateScoreError(
                    "Duplicate Score for Grader Version in one invocation",
                    details={"grader_version_id": version_key},
                )
            if item.grader_version_id != context.grader_version_id:
                raise DuplicateScoreError(
                    "Produced Score Grader Version does not match context",
                    details={
                        "expected": context.grader_version_id.value,
                        "got": version_key,
                    },
                )
            self._seen_versions.add(version_key)
            self.scores.append(item)
            self.sink.on_score(item)

    def _cleanup(self, context: GradingContext) -> None:
        try:
            self.grader.cleanup(context)
        finally:
            if self.phase is not GraderPhase.FAILED:
                self.phase = GraderPhase.CLEANED_UP
