"""Object storage adapter tests."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
from agent_eval_infrastructure.storage import (
    InMemoryObjectStorage,
    S3CompatibleObjectStorage,
)
from botocore.exceptions import ClientError


def test_in_memory_object_storage_roundtrip() -> None:
    store = InMemoryObjectStorage()
    meta = store.put("runs/r1/log.txt", b"hello", content_type="text/plain")
    assert meta.size_bytes == 5
    assert store.get("runs/r1/log.txt") == b"hello"
    head = store.head("runs/r1/log.txt")
    assert head is not None
    assert head.content_type == "text/plain"
    store.delete("runs/r1/log.txt")
    assert store.head("runs/r1/log.txt") is None
    with pytest.raises(LookupError):
        store.get("runs/r1/log.txt")


def test_s3_compatible_storage_with_mocked_client() -> None:
    client = MagicMock()
    client.put_object.return_value = {"ETag": '"abc123"'}
    body = MagicMock()
    body.read.return_value = b"payload"
    client.get_object.return_value = {"Body": body}
    client.head_object.return_value = {
        "ETag": '"abc123"',
        "ContentType": "application/json",
        "ContentLength": 7,
    }

    store = S3CompatibleObjectStorage(client, bucket="artifacts")
    meta = store.put("k1", b"payload", content_type="application/json")
    assert meta.etag == "abc123"
    assert store.get("k1") == b"payload"
    head = store.head("k1")
    assert head is not None
    assert head.size_bytes == 7
    store.delete("k1")
    client.delete_object.assert_called_once()


def test_s3_get_missing_maps_to_lookup_error() -> None:
    client = MagicMock()
    error_response: dict[str, Any] = {"Error": {"Code": "NoSuchKey", "Message": "x"}}
    client.get_object.side_effect = ClientError(error_response, "GetObject")
    store = S3CompatibleObjectStorage(client, bucket="artifacts")
    with pytest.raises(LookupError):
        store.get("missing")
