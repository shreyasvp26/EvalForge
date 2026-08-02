"""ID generation port.

Domain IDs are opaque non-empty strings. Generation strategy (UUID, ULID, …)
is an Application/Infrastructure concern (Domain ``common/ids.py``).
"""

from __future__ import annotations

from typing import Protocol
from uuid import uuid4


class IdGenerator(Protocol):
    """Produces new opaque identity strings for aggregates and entities."""

    def new_id(self) -> str: ...


class UuidIdGenerator:
    """Default stdlib UUID4 generator — framework-free, safe for Application."""

    def new_id(self) -> str:
        return str(uuid4())
