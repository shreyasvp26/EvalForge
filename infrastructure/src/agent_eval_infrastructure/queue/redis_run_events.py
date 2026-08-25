"""Redis-backed live run event fan-out (worker publish → API SSE subscribe).

Durable ``execution_events`` remain the source of truth. This channel only
notifies listeners that new durable records (or status changes) exist so the
API can stream without busy-polling the database.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any, Protocol


class RedisPubSubClient(Protocol):
    def publish(self, channel: str, message: str) -> object: ...

    def pubsub(self, **kwargs: Any) -> Any: ...


class RedisRunEventFanout:
    """Publish run event / status notifications after durable persistence."""

    def __init__(
        self,
        client: RedisPubSubClient,
        *,
        channel_prefix: str = "evalforge:run-events",
    ) -> None:
        self._client = client
        self._channel_prefix = channel_prefix.rstrip(":")

    def channel_for(self, run_id: str) -> str:
        return f"{self._channel_prefix}:{run_id}"

    def publish_event(
        self,
        *,
        run_id: str,
        event_id: str,
        sequence: int,
        kind: str,
        already_recorded: bool = False,
    ) -> None:
        payload = {
            "type": "execution_event",
            "run_id": run_id,
            "event_id": event_id,
            "sequence": sequence,
            "kind": kind,
            "already_recorded": already_recorded,
        }
        self._client.publish(self.channel_for(run_id), json.dumps(payload))

    def publish_artifact(
        self,
        *,
        run_id: str,
        artifact_id: str,
        kind: str,
    ) -> None:
        payload = {
            "type": "artifact",
            "run_id": run_id,
            "artifact_id": artifact_id,
            "kind": kind,
        }
        self._client.publish(self.channel_for(run_id), json.dumps(payload))

    def publish_status(self, *, run_id: str, status: str) -> None:
        payload = {
            "type": "run_status",
            "run_id": run_id,
            "status": status,
        }
        self._client.publish(self.channel_for(run_id), json.dumps(payload))


class RedisRunEventListener:
    """Subscribe to a single run's notification channel."""

    def __init__(
        self,
        client: RedisPubSubClient,
        *,
        channel_prefix: str = "evalforge:run-events",
    ) -> None:
        self._client = client
        self._channel_prefix = channel_prefix.rstrip(":")

    def listen(
        self,
        run_id: str,
        *,
        timeout_seconds: float = 1.0,
    ) -> Iterator[dict[str, Any]]:
        channel = f"{self._channel_prefix}:{run_id}"
        pubsub = self._client.pubsub(ignore_subscribe_messages=True)
        try:
            pubsub.subscribe(channel)
            while True:
                message = pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=timeout_seconds,
                )
                if message is None:
                    yield {"type": "heartbeat"}
                    continue
                if message.get("type") != "message":
                    continue
                data = message.get("data")
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                if not isinstance(data, str):
                    continue
                try:
                    parsed = json.loads(data)
                except json.JSONDecodeError:
                    continue
                if isinstance(parsed, dict):
                    yield parsed
        finally:
            try:
                pubsub.unsubscribe(channel)
                pubsub.close()
            except Exception:  # noqa: BLE001 — best-effort cleanup
                pass
