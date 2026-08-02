"""UUID-based ID generator implementing the Application ``IdGenerator`` port.

Domain IDs remain opaque strings; UUID is an Infrastructure/Application
generation strategy, never leaked into Domain types.
"""

from __future__ import annotations

from uuid import uuid4


class UuidIdGenerator:
    """Produces opaque UUID4 identity strings for aggregates and entities."""

    def new_id(self) -> str:
        return str(uuid4())
