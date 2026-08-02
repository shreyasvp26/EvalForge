"""Domain event dispatch abstraction.

Aggregates record events via ``pull_events()``. Application collects them after
successful Domain operations and dispatches through this port *after* commit
so consumers never see uncommitted facts. Concrete outbox / bus / in-process
handlers live in Infrastructure.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from agent_eval_domain.common.events import DomainEvent


class DomainEventDispatcher(Protocol):
    """Publishes domain events after a successful unit of work."""

    def dispatch(self, events: Sequence[DomainEvent]) -> None: ...
