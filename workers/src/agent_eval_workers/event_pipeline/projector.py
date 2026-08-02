"""Projection fan-out — notify subscribers after durable Application writes."""

from __future__ import annotations

from dataclasses import dataclass, field

from agent_eval_application.dto.run import ArtifactRecordDTO, ExecutionEventRecordDTO

from agent_eval_workers.event_pipeline.ports import EventProjector


@dataclass(slots=True)
class ProjectionHub:
    """In-process fan-out to zero or more ``EventProjector`` subscribers."""

    _subscribers: list[EventProjector] = field(default_factory=list)

    def subscribe(self, projector: EventProjector) -> None:
        self._subscribers.append(projector)

    def notify_event(self, record: ExecutionEventRecordDTO) -> None:
        for projector in self._subscribers:
            projector.on_event_persisted(record)

    def notify_artifact(self, record: ArtifactRecordDTO) -> None:
        for projector in self._subscribers:
            projector.on_artifact_persisted(record)
