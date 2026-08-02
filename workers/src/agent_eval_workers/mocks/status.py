"""In-memory Run status projection (Application stand-in for orchestration tests)."""

from __future__ import annotations

from dataclasses import dataclass, field

from agent_eval_domain.common.ids import RunId

from agent_eval_workers.lifecycle.triggers import FailureCause


@dataclass(slots=True)
class RecordingRunStatus:
    """Records Domain status projection calls without Infrastructure."""

    running: list[RunId] = field(default_factory=list)
    grading: list[RunId] = field(default_factory=list)
    completed: list[RunId] = field(default_factory=list)
    failed: list[tuple[RunId, FailureCause]] = field(default_factory=list)
    cancelled: list[RunId] = field(default_factory=list)

    def project_running(self, run_id: RunId) -> None:
        self.running.append(run_id)

    def project_grading(self, run_id: RunId) -> None:
        self.grading.append(run_id)

    def project_completed(self, run_id: RunId) -> None:
        self.completed.append(run_id)

    def project_failed(self, run_id: RunId, *, cause: FailureCause) -> None:
        self.failed.append((run_id, cause))

    def project_cancelled(self, run_id: RunId) -> None:
        self.cancelled.append(run_id)
