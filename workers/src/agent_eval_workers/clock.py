"""Clock port for deterministic timeout monitoring in tests."""

from __future__ import annotations

import time
from typing import Protocol


class Clock(Protocol):
    """Monotonic time source used by timeout monitoring."""

    def monotonic(self) -> float: ...


class SystemClock:
    """Production clock backed by ``time.monotonic``."""

    def monotonic(self) -> float:
        return time.monotonic()


class FakeClock:
    """Manually advanced clock for deterministic tests."""

    def __init__(self, start: float = 0.0) -> None:
        self._now = start

    def monotonic(self) -> float:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now += seconds
