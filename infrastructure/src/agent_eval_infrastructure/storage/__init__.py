"""Object storage adapters for Artifact payloads."""

from agent_eval_infrastructure.storage.memory import InMemoryObjectStorage
from agent_eval_infrastructure.storage.protocol import ObjectMetadata, ObjectStorage
from agent_eval_infrastructure.storage.s3 import (
    S3CompatibleObjectStorage,
    create_s3_client,
)

__all__ = [
    "InMemoryObjectStorage",
    "ObjectMetadata",
    "ObjectStorage",
    "S3CompatibleObjectStorage",
    "create_s3_client",
]
