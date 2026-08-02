"""Grader execution entry points — including isolated multi-grader runs."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from agent_eval_graders.sdk.context import GradingContext
from agent_eval_graders.sdk.exceptions import DuplicateScoreError, GraderError
from agent_eval_graders.sdk.grader import Grader
from agent_eval_graders.sdk.lifecycle import LifecycleDriver
from agent_eval_graders.sdk.models import GradingOutcome, ProducedScore
from agent_eval_graders.sdk.ports import ScoreSink


@dataclass(frozen=True, slots=True)
class GraderResult:
    outcome: GradingOutcome
    scores: tuple[ProducedScore, ...]


@dataclass
class RecordingScoreSink:
    """In-memory ScoreSink for tests and isolated runners."""

    scores: list[ProducedScore] = field(default_factory=list)
    failures: list[tuple[str, str, str]] = field(default_factory=list)
    _versions: set[str] = field(default_factory=set)

    def on_score(self, produced: ProducedScore) -> None:
        key = produced.grader_version_id.value
        if key in self._versions:
            raise DuplicateScoreError(
                "Duplicate Score across graders for Grader Version",
                details={"grader_version_id": key},
            )
        self._versions.add(key)
        self.scores.append(produced)

    def on_failure(
        self,
        *,
        grader_id: str,
        grader_version_id: str,
        message: str,
    ) -> None:
        self.failures.append((grader_id, grader_version_id, message))


@dataclass(frozen=True, slots=True)
class IsolatedGradingResult:
    """Aggregate result of running many Graders independently."""

    results: tuple[tuple[str, GraderResult | None, str | None], ...]
    scores: tuple[ProducedScore, ...]
    failures: tuple[tuple[str, str, str], ...]

    @property
    def succeeded_count(self) -> int:
        return sum(
            1
            for _, result, err in self.results
            if err is None
            and result is not None
            and result.outcome is GradingOutcome.SUCCEEDED
        )

    @property
    def failed_count(self) -> int:
        return sum(
            1
            for _, result, err in self.results
            if err is not None
            or (result is not None and result.outcome is not GradingOutcome.SUCCEEDED)
        )


def run_grader(
    grader: Grader,
    context: GradingContext,
    sink: ScoreSink,
) -> GraderResult:
    """Run one complete Grader lifecycle against ``context``."""
    driver = LifecycleDriver(grader=grader, sink=sink)
    outcome = driver.run(context)
    return GraderResult(outcome=outcome, scores=tuple(driver.scores))


def run_graders_isolated(
    invocations: Sequence[tuple[str, Grader, GradingContext]],
    *,
    sink: RecordingScoreSink | None = None,
) -> IsolatedGradingResult:
    """Run many Graders independently.

    Failures never affect sibling graders (Grader Architecture — Isolation).
    """
    shared_sink = sink or RecordingScoreSink()
    results: list[tuple[str, GraderResult | None, str | None]] = []

    for name, grader, context in invocations:
        # Fresh sink wrapper so DuplicateScoreError / sink errors stay local.
        local_sink = _IsolatingSink(shared_sink)
        try:
            result = run_grader(grader, context, local_sink)
            if result.outcome is GradingOutcome.SUCCEEDED:
                results.append((name, result, None))
            else:
                message = local_sink.last_failure or result.outcome.value
                results.append((name, result, message))
        except DuplicateScoreError as exc:
            results.append((name, None, str(exc)))
        except GraderError as exc:
            results.append((name, None, str(exc)))
        except Exception as exc:  # noqa: BLE001 — isolation boundary
            results.append((name, None, str(exc)))

    return IsolatedGradingResult(
        results=tuple(results),
        scores=tuple(shared_sink.scores),
        failures=tuple(shared_sink.failures),
    )


@dataclass
class _IsolatingSink:
    """Forwards to a shared sink; captures last failure message."""

    inner: ScoreSink
    last_failure: str | None = None

    def on_score(self, produced: ProducedScore) -> None:
        self.inner.on_score(produced)

    def on_failure(
        self,
        *,
        grader_id: str,
        grader_version_id: str,
        message: str,
    ) -> None:
        self.last_failure = message
        self.inner.on_failure(
            grader_id=grader_id,
            grader_version_id=grader_version_id,
            message=message,
        )
