"""Grader registry — identity → implementation lookup."""

from __future__ import annotations

from dataclasses import dataclass, field

from agent_eval_graders.sdk.exceptions import GraderInitializationError
from agent_eval_graders.sdk.grader import Grader


@dataclass
class GraderRegistry:
    """Maps stable grader names to factory/callables producing fresh Graders.

    Each invocation should obtain a fresh Grader instance (stateless).
    """

    _factories: dict[str, type[Grader] | object] = field(default_factory=dict)

    def register(self, name: str, factory: type[Grader] | object) -> None:
        key = name.strip()
        if not key:
            raise GraderInitializationError("Grader name must be non-empty")
        if key in self._factories:
            raise GraderInitializationError(
                f"Grader {key!r} is already registered",
                details={"name": key},
            )
        self._factories[key] = factory

    def create(self, name: str, **kwargs: object) -> Grader:
        key = name.strip()
        factory = self._factories.get(key)
        if factory is None:
            raise GraderInitializationError(
                f"Unknown grader {key!r}",
                details={"name": key, "known": sorted(self._factories)},
            )
        if isinstance(factory, type):
            return factory(**kwargs)  # type: ignore[misc]
        if callable(factory):
            return factory(**kwargs)  # type: ignore[operator]
        raise GraderInitializationError(
            f"Registered factory for {key!r} is not callable",
            details={"name": key},
        )

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._factories))
