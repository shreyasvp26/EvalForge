"""Unit of Work — Application-owned transaction boundary.

Backend Architecture §8: Application defines what must succeed or fail
together; Infrastructure executes within that boundary.
"""

from __future__ import annotations

from types import TracebackType
from typing import Protocol

from agent_eval_domain.repositories import (
    AdapterRepository,
    AgentRepository,
    CaseRepository,
    GraderRepository,
    PlatformRepository,
    ProjectRepository,
    RunRepository,
    SuiteRepository,
)


class UnitOfWork(Protocol):
    """Coordinates repositories inside one transactional boundary."""

    @property
    def projects(self) -> ProjectRepository: ...

    @property
    def suites(self) -> SuiteRepository: ...

    @property
    def cases(self) -> CaseRepository: ...

    @property
    def agents(self) -> AgentRepository: ...

    @property
    def adapters(self) -> AdapterRepository: ...

    @property
    def graders(self) -> GraderRepository: ...

    @property
    def platforms(self) -> PlatformRepository: ...

    @property
    def runs(self) -> RunRepository: ...

    def commit(self) -> None:
        """Persist all changes in this unit of work atomically."""

    def rollback(self) -> None:
        """Discard uncommitted changes."""

    def __enter__(self) -> UnitOfWork: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...


class UnitOfWorkFactory(Protocol):
    """Creates a new Unit of Work for a single use-case invocation."""

    def __call__(self) -> UnitOfWork: ...
