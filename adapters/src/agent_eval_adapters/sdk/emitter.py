"""EventEmitter — ordered, exactly-once reporting through EventSink ports."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from agent_eval_adapters.sdk.models import (
    EmittedArtifact,
    EmittedEvent,
    EmittedProgress,
)
from agent_eval_adapters.sdk.ports import EventSink


@dataclass
class EventEmitter:
    """Reports translated facts across the Adapter boundary.

    MUST NOT write to repositories or object storage — only EventSink ports.
    Guarantees:
    - emission order matches emit_* call order
    - exactly-once per event_id / artifact_id within one invocation
    """

    sink: EventSink
    _emitted_event_ids: set[str] = field(default_factory=set, init=False)
    _emitted_artifact_ids: set[str] = field(default_factory=set, init=False)
    _order: list[str] = field(default_factory=list, init=False)
    _sequence: int = field(default=0, init=False)

    def emit_event(self, event: EmittedEvent) -> bool:
        """Emit event if not already seen. Returns True when newly emitted."""
        if event.event_id in self._emitted_event_ids:
            return False
        self._emitted_event_ids.add(event.event_id)
        self._sequence += 1
        self._order.append(f"event:{event.event_id}")
        self.sink.on_event(event)
        return True

    def emit_artifact(self, artifact: EmittedArtifact) -> bool:
        if artifact.artifact_id in self._emitted_artifact_ids:
            return False
        self._emitted_artifact_ids.add(artifact.artifact_id)
        self._order.append(f"artifact:{artifact.artifact_id}")
        self.sink.on_artifact(artifact)
        return True

    def emit_progress(self, progress: EmittedProgress) -> None:
        self._order.append(f"progress:{progress.message}")
        self.sink.on_progress(progress)

    def emit_error(
        self,
        message: str,
        *,
        details: Mapping[str, object] | None = None,
    ) -> None:
        self._order.append(f"error:{message}")
        self.sink.on_error(message, details=details)

    @property
    def emission_order(self) -> tuple[str, ...]:
        return tuple(self._order)

    @property
    def event_count(self) -> int:
        return len(self._emitted_event_ids)

    @property
    def artifact_count(self) -> int:
        return len(self._emitted_artifact_ids)
