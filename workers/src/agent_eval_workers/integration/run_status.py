"""RunStatusPort ← Application lifecycle use cases."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from agent_eval_application.commands.run import (
    CancelRunCommand,
    CompleteRunCommand,
    FailRunCommand,
    RecordRunTelemetryCommand,
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
    record_telemetry: object | None = None
    event_fanout: object | None = None
    running: list[RunId] = field(default_factory=list)
    grading: list[RunId] = field(default_factory=list)
    completed: list[RunId] = field(default_factory=list)
    failed: list[tuple[RunId, FailureCause]] = field(default_factory=list)
    cancelled: list[RunId] = field(default_factory=list)
    pending_failure_detail: str | None = None
    pending_failure_cause: FailureCause | None = None
    _started_monotonic: dict[str, float] = field(default_factory=dict)

    def project_running(self, run_id: RunId) -> None:
        handle = self.sandbox_registry.get(run_id)
        self.start_run.execute(  # type: ignore[attr-defined]
            StartRunCommand(
                actor=self.actor,
                run_id=run_id.value,
                sandbox_id=handle.id,
            )
        )
        self._started_monotonic[run_id.value] = time.monotonic()
        self.running.append(run_id)
        self._publish_status(run_id, "running")

    def project_grading(self, run_id: RunId) -> None:
        self.start_grading.execute(  # type: ignore[attr-defined]
            StartGradingCommand(actor=self.actor, run_id=run_id.value)
        )
        self.grading.append(run_id)
        self._publish_status(run_id, "grading")

    def project_completed(self, run_id: RunId) -> None:
        self._record_wall_clock(run_id)
        self.complete_run.execute(  # type: ignore[attr-defined]
            CompleteRunCommand(actor=self.actor, run_id=run_id.value)
        )
        self.completed.append(run_id)
        self._publish_status(run_id, "completed")

    def project_failed(
        self,
        run_id: RunId,
        *,
        cause: FailureCause,
        detail: str | None = None,
    ) -> None:
        effective_cause = self.pending_failure_cause or cause
        self.pending_failure_cause = None
        self.failed.append((run_id, effective_cause))
        reason = (
            detail or self.pending_failure_detail or effective_cause.value
        ).strip()
        self.pending_failure_detail = None
        self._record_wall_clock(run_id)
        # Domain allows Queued→Cancelled but not Queued→Failed. If the Run never
        # reached Running (sandbox failure / timeout before StartRun), cancel.
        try:
            self.fail_run.execute(  # type: ignore[attr-defined]
                FailRunCommand(
                    actor=self.actor,
                    run_id=run_id.value,
                    reason=reason,
                    category=effective_cause.value,
                )
            )
            self._publish_status(run_id, "failed")
        except Exception:
            self.cancel_run.execute(  # type: ignore[attr-defined]
                CancelRunCommand(
                    actor=self.actor,
                    run_id=run_id.value,
                    reason=reason,
                )
            )
            self.cancelled.append(run_id)
            self._publish_status(run_id, "cancelled")

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
        self._publish_status(run_id, "cancelled")

    def _record_wall_clock(self, run_id: RunId) -> None:
        if self.record_telemetry is None:
            return
        started = self._started_monotonic.pop(run_id.value, None)
        if started is None:
            return
        wall_clock_ms = max(0, int((time.monotonic() - started) * 1000))
        try:
            self.record_telemetry.execute(  # type: ignore[attr-defined]
                RecordRunTelemetryCommand(
                    actor=self.actor,
                    run_id=run_id.value,
                    wall_clock_ms=wall_clock_ms,
                    provider_usage_available=False,
                )
            )
        except Exception:  # noqa: BLE001 — telemetry must not block terminalization
            pass

    def _publish_status(self, run_id: RunId, status: str) -> None:
        if self.event_fanout is None:
            return
        try:
            self.event_fanout.publish_status(  # type: ignore[attr-defined]
                run_id=run_id.value,
                status=status,
            )
        except Exception:  # noqa: BLE001 — fan-out must not block lifecycle
            pass
