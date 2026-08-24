"""PipelineEventSink artifact storage behavior."""

from __future__ import annotations

from agent_eval_adapters.sdk.models import EmittedArtifact
from agent_eval_domain.common.ids import RunId
from agent_eval_infrastructure.storage.memory import InMemoryObjectStorage
from agent_eval_workers.event_pipeline.models import IncomingArtifact
from agent_eval_workers.integration.event_sink import PipelineEventSink


class _CaptureStream:
    def __init__(self) -> None:
        self.artifacts: list[IncomingArtifact] = []

    def submit_event(self, event: object) -> None:
        del event

    def submit_artifact(self, artifact: IncomingArtifact) -> None:
        self.artifacts.append(artifact)

    def persist_final(self, run_id: object) -> None:
        del run_id


def test_on_artifact_uploads_bytes() -> None:
    storage = InMemoryObjectStorage()
    stream = _CaptureStream()
    sink = PipelineEventSink(
        stream=stream,
        run_id=RunId("run-1"),
        object_storage=storage,
    )
    sink.on_artifact(
        EmittedArtifact(
            artifact_id="art-1",
            kind="log",
            content=b"hello-artifact",
            content_type="text/plain",
        )
    )
    assert len(stream.artifacts) == 1
    key = stream.artifacts[0].storage_key
    assert storage.get(key) == b"hello-artifact"
    assert stream.artifacts[0].checksum.startswith("sha256:")
