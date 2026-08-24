"""EventSink ← EventPersistencePipeline (Adapters never touch repositories)."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol

from agent_eval_adapters.sdk.models import (
    EmittedArtifact,
    EmittedEvent,
    EmittedProgress,
)
from agent_eval_domain.common.ids import RunId
from agent_eval_shared.log import get_logger

from agent_eval_workers.event_pipeline.models import (
    IncomingArtifact,
    IncomingExecutionEvent,
)
from agent_eval_workers.mocks.stream import EventStreamPort

logger = get_logger("agent_eval_workers.integration.event_sink")


class ArtifactObjectStore(Protocol):
    """Minimal put surface — Infrastructure ObjectStorage satisfies this."""

    def put(self, key: str, data: bytes, *, content_type: str) -> object: ...


@dataclass
class PipelineEventSink:
    """Bridge Adapter SDK ``EventSink`` → Worker event pipeline.

    When ``object_storage`` is set, artifact bytes are uploaded before metadata
    is recorded. Without storage (unit tests), metadata-only refs are kept.
    """

    stream: EventStreamPort
    run_id: RunId
    object_storage: ArtifactObjectStore | None = None
    errors: list[tuple[str, Mapping[str, object] | None]] = field(default_factory=list)
    progress: list[EmittedProgress] = field(default_factory=list)

    def on_event(self, event: EmittedEvent) -> None:
        self.stream.submit_event(
            IncomingExecutionEvent(
                run_id=self.run_id,
                execution_event_id=event.event_id,
                action=event.action,
                artifact_ids=event.artifact_ids,
            )
        )

    def on_artifact(self, artifact: EmittedArtifact) -> None:
        checksum = hashlib.sha256(artifact.content).hexdigest()
        storage_key = f"runs/{self.run_id.value}/artifacts/{artifact.artifact_id}"
        # Map Adapter kind strings onto Domain ArtifactKind values.
        kind = artifact.kind
        if kind == "payload":
            kind = "other"
        if self.object_storage is not None:
            self.object_storage.put(
                storage_key,
                artifact.content,
                content_type=artifact.content_type,
            )
            logger.info(
                "artifact_bytes_stored",
                run_id=self.run_id.value,
                artifact_id=artifact.artifact_id,
                storage_key=storage_key,
                size_bytes=len(artifact.content),
            )
        else:
            logger.warning(
                "artifact_bytes_not_stored",
                run_id=self.run_id.value,
                artifact_id=artifact.artifact_id,
                detail="object_storage not configured; metadata only",
            )
        self.stream.submit_artifact(
            IncomingArtifact(
                run_id=self.run_id,
                artifact_id=artifact.artifact_id,
                kind=kind,
                storage_key=storage_key,
                content_type=artifact.content_type,
                size_bytes=len(artifact.content),
                checksum=f"sha256:{checksum}",
            )
        )

    def on_progress(self, progress: EmittedProgress) -> None:
        self.progress.append(progress)

    def on_error(
        self,
        message: str,
        *,
        details: Mapping[str, object] | None = None,
    ) -> None:
        self.errors.append((message, details))
