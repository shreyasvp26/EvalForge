"""Authenticated SSE stream for durable run execution events.

DB / Application reads remain authoritative. Redis pub/sub (when available)
only wakes the stream early; the generator always re-reads from GetRunEvents
and GetRun so reconnects and disconnected clients cannot lose truth.
"""

from __future__ import annotations

import json
import time
from collections.abc import Iterator
from typing import Any

from agent_eval_application.common.actor import Actor
from agent_eval_application.queries.queries import GetRunEventsQuery, GetRunQuery
from agent_eval_domain.execution.run_status import RunStatus, is_terminal
from fastapi.responses import StreamingResponse

from agent_eval_api.composition import ApplicationServices
from agent_eval_api.schemas.run import ExecutionEventResponse

_TERMINAL = frozenset({"completed", "failed", "cancelled"})


def _sse(event: str, data: dict[str, Any], *, event_id: str | None = None) -> str:
    lines: list[str] = []
    if event_id is not None:
        lines.append(f"id: {event_id}")
    lines.append(f"event: {event}")
    lines.append(f"data: {json.dumps(data, default=str)}")
    lines.append("")
    return "\n".join(lines) + "\n"


def iter_run_event_sse(
    *,
    services: ApplicationServices,
    actor: Actor,
    run_id: str,
    after_sequence: int = -1,
    redis_client: object | None = None,
    channel_prefix: str = "evalforge:run-events",
    poll_seconds: float = 1.0,
    heartbeat_seconds: float = 15.0,
) -> Iterator[str]:
    """Yield SSE frames until the run is terminal (or the client disconnects)."""
    seen_sequences: set[int] = set()
    last_heartbeat = time.monotonic()
    cursor = after_sequence

    # AuthZ + initial snapshot
    run = services.get_run.execute(GetRunQuery(actor=actor, run_id=run_id))
    yield _sse(
        "run_status",
        {"run_id": run_id, "status": run.status},
        event_id=f"status:{run.status}",
    )

    def emit_new_events() -> Iterator[str]:
        nonlocal cursor
        items = services.get_run_events.execute(
            GetRunEventsQuery(actor=actor, run_id=run_id)
        )
        for event in items:
            if event.sequence <= cursor:
                continue
            if event.sequence in seen_sequences:
                continue
            seen_sequences.add(event.sequence)
            cursor = max(cursor, event.sequence)
            payload = ExecutionEventResponse.from_dto(event).model_dump(mode="json")
            yield _sse(
                "execution_event",
                payload,
                event_id=str(event.sequence),
            )

    yield from emit_new_events()

    if run.status in _TERMINAL:
        yield _sse(
            "run_terminal",
            {
                "run_id": run_id,
                "status": run.status,
                "failure_reason": run.failure_reason,
                "failure_category": run.failure_category,
            },
            event_id=f"terminal:{run.status}",
        )
        return

    listener = None
    listen_iter = None
    if redis_client is not None:
        from agent_eval_infrastructure.queue.redis_run_events import (
            RedisRunEventListener,
        )

        listener = RedisRunEventListener(redis_client, channel_prefix=channel_prefix)
        listen_iter = listener.listen(run_id, timeout_seconds=poll_seconds)

    try:
        while True:
            notified = False
            if listen_iter is not None:
                try:
                    message = next(listen_iter)
                    notified = message.get("type") != "heartbeat"
                except StopIteration:
                    listen_iter = None
            else:
                time.sleep(poll_seconds)

            yield from emit_new_events()

            run = services.get_run.execute(GetRunQuery(actor=actor, run_id=run_id))
            if run.status in _TERMINAL or is_terminal(RunStatus(run.status)):
                yield _sse(
                    "run_status",
                    {"run_id": run_id, "status": run.status},
                    event_id=f"status:{run.status}",
                )
                yield _sse(
                    "run_terminal",
                    {
                        "run_id": run_id,
                        "status": run.status,
                        "failure_reason": run.failure_reason,
                        "failure_category": run.failure_category,
                    },
                    event_id=f"terminal:{run.status}",
                )
                return

            now = time.monotonic()
            if not notified and now - last_heartbeat >= heartbeat_seconds:
                last_heartbeat = now
                yield _sse("heartbeat", {"run_id": run_id, "status": run.status})
    finally:
        listen_iter = None


def run_event_stream_response(
    *,
    services: ApplicationServices,
    actor: Actor,
    run_id: str,
    after_sequence: int = -1,
    redis_client: object | None = None,
    channel_prefix: str = "evalforge:run-events",
) -> StreamingResponse:
    generator = iter_run_event_sse(
        services=services,
        actor=actor,
        run_id=run_id,
        after_sequence=after_sequence,
        redis_client=redis_client,
        channel_prefix=channel_prefix,
    )
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
