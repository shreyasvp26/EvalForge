"""RunReader ← Application GetRun / GetRunEvents / GetRunArtifacts."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from agent_eval_application.common.actor import Actor
from agent_eval_application.queries.queries import (
    GetRunArtifactsQuery,
    GetRunEventsQuery,
    GetRunQuery,
)
from agent_eval_domain.common.ids import ArtifactId, ExecutionEventId, RunId
from agent_eval_domain.execution.entities import Artifact, ArtifactKind, ExecutionEvent
from agent_eval_domain.execution.ndm_codec import action_from_payload
from agent_eval_domain.execution.normalized_model import action_kind_of
from agent_eval_graders.sdk.models import GradingRunMetadata


@dataclass
class ApplicationRunReader:
    """Grader ``RunReader`` backed by Application queries — no repositories."""

    run_id: RunId
    actor: Actor
    get_run: object
    get_events: object
    get_artifacts: object

    def metadata(self) -> GradingRunMetadata:
        dto = self.get_run.execute(  # type: ignore[attr-defined]
            GetRunQuery(actor=self.actor, run_id=self.run_id.value)
        )
        return GradingRunMetadata(
            run_id=RunId(dto.id),
            agent_version_id=dto.pins.agent_version_id,
            adapter_version_id=dto.pins.adapter_version_id,
            case_version_id=dto.pins.case_version_id,
            prompt_version_id=dto.pins.prompt_version_id,
            status=dto.status,
        )

    def events(self) -> Sequence[ExecutionEvent]:
        records = self.get_events.execute(  # type: ignore[attr-defined]
            GetRunEventsQuery(actor=self.actor, run_id=self.run_id.value)
        )
        out: list[ExecutionEvent] = []
        for record in records:
            action = action_from_payload(dict(record.action))
            out.append(
                ExecutionEvent(
                    id=ExecutionEventId(record.id),
                    run_id=RunId(record.run_id),
                    sequence=record.sequence,
                    kind=action_kind_of(action),
                    action=action,
                    occurred_at=record.occurred_at or datetime.now(UTC),
                    artifact_ids=tuple(ArtifactId(a) for a in record.artifact_ids),
                    metadata=dict(record.metadata),
                )
            )
        return tuple(out)

    def artifacts(self) -> Sequence[Artifact]:
        records = self.get_artifacts.execute(  # type: ignore[attr-defined]
            GetRunArtifactsQuery(actor=self.actor, run_id=self.run_id.value)
        )
        out: list[Artifact] = []
        for record in records:
            kind = (
                ArtifactKind(record.kind)
                if record.kind in {k.value for k in ArtifactKind}
                else ArtifactKind.OTHER
            )
            out.append(
                Artifact(
                    id=ArtifactId(record.id),
                    run_id=RunId(record.run_id),
                    kind=kind,
                    storage_key=record.storage_key,
                    content_type=record.content_type,
                    size_bytes=record.size_bytes,
                    checksum=record.checksum,
                    created_at=record.created_at or datetime.now(UTC),
                )
            )
        return tuple(out)
