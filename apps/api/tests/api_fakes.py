"""Test doubles for Control Plane foundation tests — no live database."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock


class FakeContainer:
    """Minimal ApiContainer stand-in for TestClient (no Infrastructure)."""

    def __init__(self, services: MagicMock, settings: Any) -> None:
        self.services = services
        self.settings = settings
        self.auth = MagicMock()
        self.infrastructure = MagicMock()
        self._ready = True

    def dispose(self) -> None:
        return None

    def readiness_checks(self) -> dict[str, str]:
        if not self._ready:
            return {"composition": "ok", "database": "unavailable"}
        return {"composition": "ok", "database": "ok"}


def mock_services() -> MagicMock:
    """Placeholder ApplicationServices for foundation tests."""
    return MagicMock(name="ApplicationServices")
