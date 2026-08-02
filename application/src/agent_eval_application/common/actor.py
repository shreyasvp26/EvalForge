"""Caller identity for Application authorization.

Authentication belongs to the API Layer. Application receives an already-
authenticated ``Actor`` and decides whether that identity may perform a
Project-scoped operation (Backend Architecture §4 / §8).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Actor:
    """Authenticated principal supplied by the API or Worker entry point."""

    id: str

    def __post_init__(self) -> None:
        if not self.id.strip():
            msg = "Actor id must be non-empty"
            raise ValueError(msg)
