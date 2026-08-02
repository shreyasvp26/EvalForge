"""Lifecycle — Run step machine hosted by the Execution Engine.

Responsibility (Execution Engine Architecture — Run Lifecycle):
- Model named orchestration stages and validated transitions
- Own sequencing and illegal-transition rejection
- Coordinate Application status projections and subsystem ports

Must NOT:
- Re-implement Domain RunStatus invariants (Domain owns those)
- Embed Adapter translation or Grader scoring
- Persist or enqueue directly (Infrastructure / Application)
"""

from agent_eval_workers.lifecycle.domain_mapping import domain_status_for
from agent_eval_workers.lifecycle.errors import IllegalLifecycleTransition
from agent_eval_workers.lifecycle.machine import RunLifecycle
from agent_eval_workers.lifecycle.orchestrator import LifecycleOrchestrator
from agent_eval_workers.lifecycle.phases import (
    TERMINAL_PHASES,
    OrchestrationPhase,
    is_terminal_phase,
)
from agent_eval_workers.lifecycle.ports import (
    AdapterPort,
    EventPipelinePort,
    GradingSchedulerPort,
    RunStatusPort,
    SandboxPort,
)
from agent_eval_workers.lifecycle.transitions import (
    LifecycleTransition,
    allowed_triggers,
)
from agent_eval_workers.lifecycle.triggers import FailureCause, LifecycleTrigger

__all__ = [
    "AdapterPort",
    "EventPipelinePort",
    "FailureCause",
    "GradingSchedulerPort",
    "IllegalLifecycleTransition",
    "LifecycleOrchestrator",
    "LifecycleTransition",
    "LifecycleTrigger",
    "OrchestrationPhase",
    "RunLifecycle",
    "RunStatusPort",
    "SandboxPort",
    "TERMINAL_PHASES",
    "allowed_triggers",
    "domain_status_for",
    "is_terminal_phase",
]
