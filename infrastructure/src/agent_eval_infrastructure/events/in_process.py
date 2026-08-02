"""In-process domain event dispatcher (Application port).

Does not publish to an external bus — handlers run synchronously after commit
in the Application orchestration path. Outbox / broker transport can wrap this
later without changing use cases.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from agent_eval_domain.common.events import DomainEvent

EventHandler = Callable[[Sequence[DomainEvent]], None]


class InProcessDomainEventDispatcher:
    """Dispatches events to registered in-process handlers."""

    def __init__(self, handlers: Sequence[EventHandler] | None = None) -> None:
        self._handlers: list[EventHandler] = list(handlers or [])
        self.dispatched: list[DomainEvent] = []

    def register(self, handler: EventHandler) -> None:
        self._handlers.append(handler)

    def dispatch(self, events: Sequence[DomainEvent]) -> None:
        batch = tuple(events)
        if not batch:
            return
        self.dispatched.extend(batch)
        for handler in self._handlers:
            handler(batch)
