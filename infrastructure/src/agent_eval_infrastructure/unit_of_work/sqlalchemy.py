"""SQLAlchemy Unit of Work — Application ``UnitOfWork`` port implementation.

Owns session and transaction lifecycle. Repositories never commit or rollback.
Domain events are never dispatched here (Application: commit → dispatch).
"""

from __future__ import annotations

from types import TracebackType

from agent_eval_domain.repositories import (
    AdapterRepository,
    AgentRepository,
    CaseRepository,
    GraderRepository,
    ProjectRepository,
    RunRepository,
    SuiteRepository,
)
from sqlalchemy.orm import Session

from agent_eval_infrastructure.database.session import SessionFactory
from agent_eval_infrastructure.database.uow_context import (
    reset_active_uow_session,
    set_active_uow_session,
)
from agent_eval_infrastructure.repositories import (
    SqlAlchemyAdapterRepository,
    SqlAlchemyAgentRepository,
    SqlAlchemyCaseRepository,
    SqlAlchemyGraderRepository,
    SqlAlchemyProjectRepository,
    SqlAlchemyRunRepository,
    SqlAlchemySuiteRepository,
)


class UnitOfWorkStateError(RuntimeError):
    """Raised when the Unit of Work is used outside its active lifecycle."""


class SqlAlchemyUnitOfWork:
    """One transactional boundary sharing a single SQLAlchemy ``Session``.

    Usage (Application Layer)::

        with uow_factory() as uow:
            uow.projects.save(project)
            uow.commit()
        # Application then dispatches domain events — never this class.
    """

    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory
        self._session: Session | None = None
        self._session_token = None
        self._committed = False
        self._projects: ProjectRepository | None = None
        self._suites: SuiteRepository | None = None
        self._cases: CaseRepository | None = None
        self._agents: AgentRepository | None = None
        self._adapters: AdapterRepository | None = None
        self._graders: GraderRepository | None = None
        self._runs: RunRepository | None = None

    @property
    def session(self) -> Session:
        """Active session for this unit of work (tests / advanced adapters)."""
        return self._require_session()

    @property
    def projects(self) -> ProjectRepository:
        return self._require_repo(self._projects, "projects")

    @property
    def suites(self) -> SuiteRepository:
        return self._require_repo(self._suites, "suites")

    @property
    def cases(self) -> CaseRepository:
        return self._require_repo(self._cases, "cases")

    @property
    def agents(self) -> AgentRepository:
        return self._require_repo(self._agents, "agents")

    @property
    def adapters(self) -> AdapterRepository:
        return self._require_repo(self._adapters, "adapters")

    @property
    def graders(self) -> GraderRepository:
        return self._require_repo(self._graders, "graders")

    @property
    def runs(self) -> RunRepository:
        return self._require_repo(self._runs, "runs")

    def commit(self) -> None:
        """Flush and commit the shared session. Propagates optimistic conflicts."""
        session = self._require_session()
        session.commit()
        self._committed = True

    def rollback(self) -> None:
        """Discard uncommitted changes on the shared session."""
        session = self._require_session()
        session.rollback()
        self._committed = False

    def __enter__(self) -> SqlAlchemyUnitOfWork:
        if self._session is not None:
            raise UnitOfWorkStateError(
                "SqlAlchemyUnitOfWork does not support nested entry; "
                "open a new Unit of Work per use-case invocation"
            )
        session = self._session_factory()
        self._session = session
        self._session_token = set_active_uow_session(session)
        self._committed = False
        self._projects = SqlAlchemyProjectRepository(session)
        self._suites = SqlAlchemySuiteRepository(session)
        self._cases = SqlAlchemyCaseRepository(session)
        self._agents = SqlAlchemyAgentRepository(session)
        self._adapters = SqlAlchemyAdapterRepository(session)
        self._graders = SqlAlchemyGraderRepository(session)
        self._runs = SqlAlchemyRunRepository(session)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        try:
            if self._session is not None and not self._committed:
                self._session.rollback()
        finally:
            self._close()

    def _require_session(self) -> Session:
        if self._session is None:
            raise UnitOfWorkStateError(
                "Unit of Work is not active; use `with uow_factory() as uow:`"
            )
        return self._session

    def _require_repo[T](self, repo: T | None, name: str) -> T:
        if repo is None:
            raise UnitOfWorkStateError(
                f"Repository `{name}` is unavailable; Unit of Work is not active"
            )
        return repo

    def _close(self) -> None:
        if self._session_token is not None:
            reset_active_uow_session(self._session_token)
            self._session_token = None
        if self._session is not None:
            self._session.close()
        self._session = None
        self._projects = None
        self._suites = None
        self._cases = None
        self._agents = None
        self._adapters = None
        self._graders = None
        self._runs = None


class SqlAlchemyUnitOfWorkFactory:
    """Creates a new ``SqlAlchemyUnitOfWork`` per Application use-case call."""

    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    def __call__(self) -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(self._session_factory)
