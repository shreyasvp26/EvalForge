"""RunStatusPort ← Application lifecycle use cases."""

from __future__ import annotations

from dataclasses import dataclass, field

from agent_eval_application.commands.run import (
    CancelRunCommand,
    CompleteRunCommand,
    FailRunCommand,
    StartGradingCommand,
    StartRunCommand,
)
from agent_eval_application.common.actor import Actor
from agent_eval_domain.common.ids import RunId

from agent_eval_workers.integration.registry import RunSandboxRegistry
from agent_eval_workers.lifecycle.triggers import FailureCause


@dataclass
class ApplicationRunStatus:
    """Project Domain Run status through Application — never direct persistence."""

    actor: Actor
    sandbox_registry: RunSandboxRegistry
    start_run: object
    start_grading: object
    complete_run: object
    fail_run: object
    cancel_run: object
    running: list[RunId] = field(default_factory=list)
    grading: list[RunId] = field(default_factory=list)
    completed: list[RunId] = field(default_factory=list)
    failed: list[tuple[RunId, FailureCause]] = field(default_factory=list)
    cancelled: list[RunId] = field(default_factory=list)

    def project_running(self, run_id: RunId) -> None:
        handle = self.sandbox_registry.get(run_id)
        self.start_run.execute(  # type: ignore[attr-defined]
            StartRunCommand(
                actor=self.actor,
                run_id=run_id.value,
                sandbox_id=handle.id,
            )
        )
        self.running.append(run_id)

    def project_grading(self, run_id: RunId) -> None:
        self.start_grading.execute(  # type: ignore[attr-defined]
            StartGradingCommand(actor=self.actor, run_id=run_id.value)
        )
        self.grading.append(run_id)

    def project_completed(self, run_id: RunId) -> None:
        self.complete_run.execute(  # type: ignore[attr-defined]
            CompleteRunCommand(actor=self.actor, run_id=run_id.value)
        )
        self.completed.append(run_id)

    def project_failed(self, run_id: RunId, *, cause: FailureCause) -> None:
        self.failed.append((run_id, cause))
        # Domain allows Queued→Cancelled but not Queued→Failed. If the Run never
        # reached Running (sandbox failure / timeout before StartRun), cancel.
        try:
            self.fail_run.execute(  # type: ignore[attr-defined]
                FailRunCommand(
                    actor=self.actor,
                    run_id=run_id.value,
                    reason=cause.value,
                )
            )
        except Exception:
            self.cancel_run.execute(  # type: ignore[attr-defined]
                CancelRunCommand(
                    actor=self.actor,
                    run_id=run_id.value,
                    reason=cause.value,
                )
            )
            self.cancelled.append(run_id)

    def project_cancelled(self, run_id: RunId) -> None:
        # Idempotent: API may have already persisted CANCELLED (queued cancel)
        # while the worker still observes the Redis cancel signal.
        try:
            self.cancel_run.execute(  # type: ignore[attr-defined]
                CancelRunCommand(
                    actor=self.actor, run_id=run_id.value, reason="cancelled"
                )
            )
        except Exception:  # noqa: BLE001 — already terminal / race with API cancel
            pass
        self.cancelled.append(run_id)
