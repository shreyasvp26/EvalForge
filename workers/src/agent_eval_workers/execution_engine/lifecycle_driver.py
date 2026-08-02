"""Lifecycle driver port — Engine orchestrates; tests may mock this surface."""

from __future__ import annotations

from typing import Protocol

from agent_eval_workers.lifecycle.phases import OrchestrationPhase
from agent_eval_workers.lifecycle.transitions import LifecycleTransition
from agent_eval_workers.lifecycle.triggers import LifecycleTrigger


class LifecycleDriver(Protocol):
    """Narrow façade over RunLifecycle / LifecycleOrchestrator for the Engine."""

    @property
    def phase(self) -> OrchestrationPhase: ...

    @property
    def is_terminal(self) -> bool: ...

    def apply(self, trigger: LifecycleTrigger) -> LifecycleTransition: ...
