"""Shared aggregate helpers."""

from __future__ import annotations

from agent_eval_domain.common.events import DomainEvent, EventCollector


class AggregateRoot:
    """Base for aggregate roots that emit domain events."""

    def __init__(self) -> None:
        self._domain_events = EventCollector()

    def pull_events(self) -> tuple[DomainEvent, ...]:
        return self._domain_events.pull()

    def _record(self, event: DomainEvent) -> None:
        self._domain_events.raise_(event)
