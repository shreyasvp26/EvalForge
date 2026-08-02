"""In-memory Application event writer for end-to-end orchestration tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from agent_eval_application.commands.run import (
    RecordArtifactCommand,
    RecordExecutionEventCommand,
)
from agent_eval_application.dto.run import ArtifactRecordDTO, ExecutionEventRecordDTO
from agent_eval_domain.execution.ndm_codec import action_from_payload
from agent_eval_domain.execution.normalized_model import action_kind_of


@dataclass(slots=True)
class InMemoryEventWriter:
    """Deterministic, idempotent ApplicationEventWriter (no Postgres)."""

    events: list[ExecutionEventRecordDTO] = field(default_factory=list)
    artifacts: list[ArtifactRecordDTO] = field(default_factory=list)
    _events_by_id: dict[str, ExecutionEventRecordDTO] = field(default_factory=dict)
    _artifacts_by_id: dict[str, ArtifactRecordDTO] = field(default_factory=dict)
    _sequences: dict[str, int] = field(default_factory=dict)
    event_write_order: list[str] = field(default_factory=list)
    artifact_write_order: list[str] = field(default_factory=list)

    def record_execution_event(
        self, command: RecordExecutionEventCommand
    ) -> ExecutionEventRecordDTO:
        existing = self._events_by_id.get(command.execution_event_id)
        if existing is not None:
            return ExecutionEventRecordDTO(
                id=existing.id,
                run_id=existing.run_id,
                sequence=existing.sequence,
                kind=existing.kind,
                artifact_ids=existing.artifact_ids,
                occurred_at=existing.occurred_at,
                already_recorded=True,
            )
        action = action_from_payload(dict(command.action))
        seq = self._sequences.get(command.run_id, 0)
        self._sequences[command.run_id] = seq + 1
        dto = ExecutionEventRecordDTO(
            id=command.execution_event_id,
            run_id=command.run_id,
            sequence=seq,
            kind=action_kind_of(action).value,
            artifact_ids=command.artifact_ids,
            occurred_at=command.occurred_at or datetime.now(tz=UTC),
            already_recorded=False,
        )
        self._events_by_id[dto.id] = dto
        self.events.append(dto)
        self.event_write_order.append(dto.id)
        return dto

    def record_artifact(self, command: RecordArtifactCommand) -> ArtifactRecordDTO:
        assert command.artifact_id is not None
        existing = self._artifacts_by_id.get(command.artifact_id)
        if existing is not None:
            return ArtifactRecordDTO(
                id=existing.id,
                run_id=existing.run_id,
                kind=existing.kind,
                storage_key=existing.storage_key,
                content_type=existing.content_type,
                size_bytes=existing.size_bytes,
                checksum=existing.checksum,
                already_recorded=True,
            )
        dto = ArtifactRecordDTO(
            id=command.artifact_id,
            run_id=command.run_id,
            kind=command.kind,
            storage_key=command.storage_key,
            content_type=command.content_type,
            size_bytes=command.size_bytes,
            checksum=command.checksum,
            already_recorded=False,
        )
        self._artifacts_by_id[dto.id] = dto
        self.artifacts.append(dto)
        self.artifact_write_order.append(dto.id)
        return dto
