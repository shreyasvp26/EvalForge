"""Ports the lifecycle orchestrator invokes — interfaces only (Phase 2).

Concrete Sandbox / Adapter / Grader / persistence implementations arrive in
later phases. Lifecycle never embeds their logic.
"""

from __future__ import annotations

from typing import Protocol

from agent_eval_domain.common.ids import RunId

from agent_eval_workers.lifecycle.triggers import FailureCause


class SandboxPort(Protocol):
    """Sandbox provision / destroy boundary (Execution Engine Architecture)."""

    def provision(self, run_id: RunId) -> None: ...

    def destroy(self, run_id: RunId) -> None: ...


class AdapterPort(Protocol):
    """Adapter boundary — translation + streaming live inside Adapters."""

    def start(self, run_id: RunId) -> None: ...

    def run(self, run_id: RunId) -> None:
        """Execute inside the Sandbox and stream events/artifacts continuously."""
        ...

    def finish(self, run_id: RunId) -> None: ...


class EventPipelinePort(Protocol):
    """Final event / artifact flush before grading is scheduled."""

    def persist_final(self, run_id: RunId) -> None: ...


class GradingSchedulerPort(Protocol):
    """Schedule Grader invocations — Graders own scoring, not this port."""

    def schedule(self, run_id: RunId) -> None: ...


class RunStatusPort(Protocol):
    """Application-mediated Domain status updates (no direct persistence)."""

    def project_running(self, run_id: RunId) -> None: ...

    def project_grading(self, run_id: RunId) -> None: ...

    def project_completed(self, run_id: RunId) -> None: ...

    def project_failed(self, run_id: RunId, *, cause: FailureCause) -> None: ...

    def project_cancelled(self, run_id: RunId) -> None: ...
