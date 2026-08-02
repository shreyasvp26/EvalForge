"""Execution Engine — standing platform capability (not an instance entity).

This domain service expresses orchestration invariants without implementing
sandbox provisioning, adapter invocation, or persistence.
"""

from __future__ import annotations

from dataclasses import dataclass

from agent_eval_domain.common.errors import InvariantViolation
from agent_eval_domain.common.ids import (
    AdapterVersionId,
    SandboxId,
)
from agent_eval_domain.execution.entities import Sandbox
from agent_eval_domain.execution.run import EvaluationRun
from agent_eval_domain.execution.run_status import RunStatus


@dataclass(frozen=True, slots=True)
class ExecutionEngine:
    """Agent-agnostic orchestrator of a single Run invocation (Invariant 8).

    Concrete provisioning and adapter I/O live outside Domain. This type
    encodes what must be true when those steps succeed.
    """

    def begin_execution(
        self,
        run: EvaluationRun,
        *,
        sandbox_id: SandboxId,
        adapter_version_id: AdapterVersionId,
    ) -> Sandbox:
        """Transition Run to Running and provision a fresh Sandbox."""
        if adapter_version_id != run.pins.adapter_version_id:
            raise InvariantViolation(
                "Execution Engine must invoke the Adapter Version pinned on the Run",
                code="ADAPTER_PIN_MISMATCH",
                details={
                    "pinned": run.pins.adapter_version_id.value,
                    "requested": adapter_version_id.value,
                },
            )
        if run.status is not RunStatus.QUEUED:
            raise InvariantViolation(
                "Execution may only begin from Queued",
                code="EXECUTION_WRONG_PHASE",
                details={"status": run.status.value},
            )
        return run.start(sandbox_id=sandbox_id)

    def assert_agent_agnostic(self) -> None:
        """Documentation hook: engine never branches on vendor identity."""
        return None

    def finish_execution_successfully(self, run: EvaluationRun) -> None:
        """Move from Running into Grading after agent activity concludes."""
        if run.status is not RunStatus.RUNNING:
            raise InvariantViolation(
                "Successful execution finish requires Running state",
                code="EXECUTION_FINISH_WRONG_PHASE",
                details={"status": run.status.value},
            )
        run.start_grading()

    def fail_execution(self, run: EvaluationRun, *, reason: str) -> None:
        """Platform/infrastructure failure during execution — not agent task failure."""
        if run.status not in {RunStatus.RUNNING, RunStatus.QUEUED}:
            raise InvariantViolation(
                "Execution failure is only valid from Queued or Running",
                code="EXECUTION_FAIL_WRONG_PHASE",
                details={"status": run.status.value},
            )
        if run.status is RunStatus.QUEUED:
            # Queued → Cancelled is the only path that closes without Running;
            # platform failure before start is modeled as Failed via Running path
            # is not allowed from Queued. Domain Model: Queued → Cancelled or Running.
            # Treat pre-start platform abort as Cancelled for queue withdrawal,
            # and Failed only once Running. Application layer chooses; we expose both.
            run.cancel(reason=reason)
            return
        run.fail(reason=reason)
