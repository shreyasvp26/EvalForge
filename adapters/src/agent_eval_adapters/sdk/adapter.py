"""Adapter contract — translation boundary only."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Protocol, runtime_checkable

from agent_eval_adapters.sdk.capabilities import AdapterCapabilities
from agent_eval_adapters.sdk.context import ExecutionContext
from agent_eval_adapters.sdk.models import AdapterOutcome, NativeObservation


@runtime_checkable
class Adapter(Protocol):
    """Uniform Adapter contract (Adapter Architecture — Adapter Contract).

    Lifecycle: initialize → prepare → start → stream → finish → cleanup.
    Invocations are stateless — no durable state across runs.
    """

    @property
    def name(self) -> str: ...

    @property
    def capabilities(self) -> AdapterCapabilities: ...

    def initialize(self, context: ExecutionContext) -> None:
        """Establish observation against the prepared Sandbox."""
        ...

    def prepare(self, context: ExecutionContext) -> None:
        """Deliver prompt / stage agent inputs inside the Sandbox."""
        ...

    def start(self, context: ExecutionContext) -> None:
        """Begin Agent process / observation hooks."""
        ...

    def stream(self, context: ExecutionContext) -> Iterator[NativeObservation]:
        """Yield native observations continuously during Agent execution."""
        ...

    def finish(
        self,
        context: ExecutionContext,
        observations: tuple[NativeObservation, ...],
    ) -> AdapterOutcome:
        """Translate concluding signal; do not tear down the Sandbox."""
        ...

    def cleanup(self, context: ExecutionContext) -> None:
        """Release transient in-memory state only."""
        ...


class BaseAdapter:
    """Optional base with no-op defaults for prepare/cleanup."""

    name: str = "base"
    capabilities: AdapterCapabilities = AdapterCapabilities()

    def initialize(self, context: ExecutionContext) -> None:
        del context

    def prepare(self, context: ExecutionContext) -> None:
        del context

    def start(self, context: ExecutionContext) -> None:
        del context

    def stream(self, context: ExecutionContext) -> Iterator[NativeObservation]:
        del context
        yield from ()

    def finish(
        self,
        context: ExecutionContext,
        observations: tuple[NativeObservation, ...],
    ) -> AdapterOutcome:
        del context, observations
        return AdapterOutcome.COMPLETED

    def cleanup(self, context: ExecutionContext) -> None:
        del context
