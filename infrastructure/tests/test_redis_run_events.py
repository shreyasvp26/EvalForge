"""Tests for Redis run-event fan-out used by SSE."""

from __future__ import annotations

import json
from collections import defaultdict

from agent_eval_infrastructure.queue.redis_run_events import RedisRunEventFanout


class _FakePubSubRedis:
    def __init__(self) -> None:
        self.published: list[tuple[str, str]] = []
        self._channels: dict[str, list[str]] = defaultdict(list)

    def publish(self, channel: str, message: str) -> int:
        self.published.append((channel, message))
        self._channels[channel].append(message)
        return 1


def test_fanout_publishes_execution_event_payload() -> None:
    client = _FakePubSubRedis()
    fanout = RedisRunEventFanout(client, channel_prefix="evalforge:run-events")
    fanout.publish_event(
        run_id="run-1",
        event_id="evt-1",
        sequence=3,
        kind="message",
    )
    assert len(client.published) == 1
    channel, raw = client.published[0]
    assert channel == "evalforge:run-events:run-1"
    payload = json.loads(raw)
    assert payload["type"] == "execution_event"
    assert payload["sequence"] == 3
    assert payload["event_id"] == "evt-1"


def test_fanout_publishes_status() -> None:
    client = _FakePubSubRedis()
    fanout = RedisRunEventFanout(client)
    fanout.publish_status(run_id="run-9", status="completed")
    _, raw = client.published[0]
    assert json.loads(raw) == {
        "type": "run_status",
        "run_id": "run-9",
        "status": "completed",
    }
