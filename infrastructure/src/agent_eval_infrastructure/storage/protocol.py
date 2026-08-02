"""Object storage contracts for Artifact payloads (S3-compatible providers)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ObjectMetadata:
    """Minimal metadata returned by put/head — no provider-specific fields."""

    key: str
    content_type: str
    size_bytes: int
    etag: str | None = None


class ObjectStorage(Protocol):
    """Provider-agnostic object storage for Artifact bytes.

    Keys are opaque storage keys owned by Domain ``Artifact.storage_key``.
    Implementations must not hardcode a single cloud vendor.
    """

    def put(
        self,
        key: str,
        data: bytes,
        *,
        content_type: str,
    ) -> ObjectMetadata:
        """Upload bytes and return stored metadata."""

    def get(self, key: str) -> bytes:
        """Download object bytes. Raise ``LookupError`` if missing."""

    def delete(self, key: str) -> None:
        """Delete an object. Missing keys are a no-op."""

    def head(self, key: str) -> ObjectMetadata | None:
        """Return metadata without downloading the body, or None if missing."""
