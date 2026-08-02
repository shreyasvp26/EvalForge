"""Domain event primitives.

Events are immutable business facts. Propagation (queue, bus, outbox) is
outside Domain scope — aggregates only *record* that an event occurred.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True, kw_only=True)
class DomainEvent:
    """Base domain event."""

    event_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = field(default_factory=utc_now)
    event_type: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_type", type(self).__name__)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "occurred_at": self.occurred_at.isoformat(),
        }


class EventCollector:
    """Collects domain events raised during a single aggregate operation."""

    def __init__(self) -> None:
        self._events: list[DomainEvent] = []

    def raise_(self, event: DomainEvent) -> None:
        self._events.append(event)

    def pull(self) -> tuple[DomainEvent, ...]:
        events = tuple(self._events)
        self._events.clear()
        return events

    def peek(self) -> tuple[DomainEvent, ...]:
        return tuple(self._events)
