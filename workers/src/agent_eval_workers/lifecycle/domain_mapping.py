"""Map Engine orchestration phases to Domain ``RunStatus`` projections.

Domain owns the persisted Run status machine. Orchestration phases are finer
grained and never replace Domain transitions — they inform when Application
should be asked to advance Domain status.
"""

from __future__ import annotations

from agent_eval_domain.execution.run_status import RunStatus

from agent_eval_workers.lifecycle.phases import OrchestrationPhase

_PHASE_TO_DOMAIN: dict[OrchestrationPhase, RunStatus] = {
    OrchestrationPhase.QUEUED: RunStatus.QUEUED,
    OrchestrationPhase.CLAIMED: RunStatus.RUNNING,
    OrchestrationPhase.SANDBOX_PROVISIONING: RunStatus.RUNNING,
    OrchestrationPhase.SANDBOX_READY: RunStatus.RUNNING,
    OrchestrationPhase.ADAPTER_STARTING: RunStatus.RUNNING,
    OrchestrationPhase.EXECUTION_STREAMING: RunStatus.RUNNING,
    OrchestrationPhase.ADAPTER_FINISHED: RunStatus.RUNNING,
    OrchestrationPhase.FINAL_EVENT_PERSISTENCE: RunStatus.RUNNING,
    OrchestrationPhase.GRADING_SCHEDULED: RunStatus.GRADING,
    OrchestrationPhase.COMPLETED: RunStatus.COMPLETED,
    OrchestrationPhase.FAILED: RunStatus.FAILED,
    OrchestrationPhase.CANCELLED: RunStatus.CANCELLED,
}


def domain_status_for(phase: OrchestrationPhase) -> RunStatus:
    """Return the Domain status projection for an orchestration phase."""
    return _PHASE_TO_DOMAIN[phase]
