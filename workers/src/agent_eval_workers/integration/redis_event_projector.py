"""Worker projector that fans durable event writes to Redis for SSE."""

from __future__ import annotations

from dataclasses import dataclass

from agent_eval_application.dto.run import ArtifactRecordDTO, ExecutionEventRecordDTO


@dataclass(slots=True)
class RedisEventFanoutProjector:
    """``EventProjector`` → Redis pub/sub (no-op when fanout is absent)."""

    fanout: object | None

    def on_event_persisted(self, record: ExecutionEventRecordDTO) -> None:
        if self.fanout is None:
            return
        self.fanout.publish_event(  # type: ignore[attr-defined]
            run_id=record.run_id,
            event_id=record.id,
            sequence=record.sequence,
            kind=record.kind,
            already_recorded=record.already_recorded,
        )

    def on_artifact_persisted(self, record: ArtifactRecordDTO) -> None:
        if self.fanout is None:
            return
        self.fanout.publish_artifact(  # type: ignore[attr-defined]
            run_id=record.run_id,
            artifact_id=record.id,
            kind=record.kind,
        )
