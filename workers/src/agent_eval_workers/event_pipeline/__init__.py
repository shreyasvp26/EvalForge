"""Event pipeline — Execution Event / Artifact streaming into persistence.

Responsibility (Execution Engine Architecture — continuous recording):
- Accept Normalized Domain Model actions streamed from the Adapter / Engine
- Preserve strict emission order within a Run
- Persist Execution Events and Artifact metadata through Application use cases
- Ensure append-only, idempotent durable recording
- Expose projection hooks for future SSE / WebSocket / dashboard consumers

Must NOT:
- Translate vendor-native actions (Adapter owns translation)
- Grade or interpret events (Grader owns scoring)
- Implement SSE or HTTP streaming (API Layer)
- Bypass Application to write repositories or mutate past events
- Overwrite Artifacts or modify Run history
"""

from agent_eval_workers.event_pipeline.errors import PersistenceFailure
from agent_eval_workers.event_pipeline.models import (
    IncomingArtifact,
    IncomingExecutionEvent,
)
from agent_eval_workers.event_pipeline.pipeline import (
    EventPersistencePipeline,
    UseCaseEventWriter,
)
from agent_eval_workers.event_pipeline.ports import (
    ApplicationEventWriter,
    EventProjector,
)
from agent_eval_workers.event_pipeline.projector import ProjectionHub

__all__ = [
    "ApplicationEventWriter",
    "EventPersistencePipeline",
    "EventProjector",
    "IncomingArtifact",
    "IncomingExecutionEvent",
    "PersistenceFailure",
    "ProjectionHub",
    "UseCaseEventWriter",
]
