"""Mock grading scheduler — invokes Graders only after execution completes."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from agent_eval_domain.common.ids import RunId

from agent_eval_workers.mocks.grader import MockGrader, MockScore


@dataclass
class MockGradingScheduler:
    """``GradingSchedulerPort`` — synchronous, isolated mock grading.

    Invoked by the Lifecycle only after Final Event Persistence / grading
    scheduling. Never during Adapter execution.
    """

    graders: tuple[MockGrader, ...] = ()
    scores: list[MockScore] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    scheduled: list[RunId] = field(default_factory=list)
    after_schedule: Callable[[RunId], None] | None = None

    def schedule(self, run_id: RunId) -> None:
        self.scheduled.append(run_id)
        for grader in self.graders:
            try:
                result = grader.grade(run_id)
            except Exception as exc:  # noqa: BLE001 — isolation boundary
                self.failures.append(f"{grader.grader_id}:{exc}")
                continue
            if result is None:
                self.failures.append(grader.grader_id)
            else:
                self.scores.append(result)
        if self.after_schedule is not None:
            self.after_schedule(run_id)
