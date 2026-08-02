"""In-memory object storage for deterministic unit tests."""

from __future__ import annotations

from dataclasses import dataclass

from agent_eval_infrastructure.storage.protocol import ObjectMetadata


@dataclass
class _StoredObject:
    data: bytes
    content_type: str


class InMemoryObjectStorage:
    """Process-local ObjectStorage implementing put/get/delete/head."""

    def __init__(self) -> None:
        self._objects: dict[str, _StoredObject] = {}

    def put(self, key: str, data: bytes, *, content_type: str) -> ObjectMetadata:
        self._objects[key] = _StoredObject(data=data, content_type=content_type)
        return ObjectMetadata(
            key=key,
            content_type=content_type,
            size_bytes=len(data),
            etag=str(len(data)),
        )

    def get(self, key: str) -> bytes:
        try:
            return self._objects[key].data
        except KeyError as exc:
            raise LookupError(f"Object not found: {key}") from exc

    def delete(self, key: str) -> None:
        self._objects.pop(key, None)

    def head(self, key: str) -> ObjectMetadata | None:
        stored = self._objects.get(key)
        if stored is None:
            return None
        return ObjectMetadata(
            key=key,
            content_type=stored.content_type,
            size_bytes=len(stored.data),
            etag=str(len(stored.data)),
        )
