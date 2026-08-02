"""Domain event dispatch adapters."""

from agent_eval_infrastructure.events.in_process import (
    EventHandler,
    InProcessDomainEventDispatcher,
)

__all__ = ["EventHandler", "InProcessDomainEventDispatcher"]
