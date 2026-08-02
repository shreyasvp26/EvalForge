"""Shared orchestration helpers for use cases."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import asdict, is_dataclass
from typing import Any

from agent_eval_domain.common.aggregate import AggregateRoot
from agent_eval_domain.common.errors import DomainError
from agent_eval_domain.common.events import DomainEvent

from agent_eval_application.common.actor import Actor
from agent_eval_application.errors import (
    ConflictError,
    translate_domain_error,
)
from agent_eval_application.ports.event_dispatcher import DomainEventDispatcher
from agent_eval_application.ports.idempotency import IdempotencyStatus, IdempotencyStore
from agent_eval_application.ports.unit_of_work import UnitOfWork, UnitOfWorkFactory


def collect_events(*aggregates: AggregateRoot) -> list[DomainEvent]:
    events: list[DomainEvent] = []
    for aggregate in aggregates:
        events.extend(aggregate.pull_events())
    return events


def commit_and_dispatch(
    uow: UnitOfWork,
    dispatcher: DomainEventDispatcher,
    events: Sequence[DomainEvent],
) -> None:
    uow.commit()
    if events:
        dispatcher.dispatch(events)


def dto_to_idempotency_payload(dto: object) -> dict[str, Any]:
    if is_dataclass(dto) and not isinstance(dto, type):
        return asdict(dto)
    msg = f"Cannot serialize result of type {type(dto)!r}"
    raise TypeError(msg)


def run_in_uow[T](
    uow_factory: UnitOfWorkFactory,
    dispatcher: DomainEventDispatcher,
    work: Callable[[UnitOfWork], tuple[T, list[DomainEvent]]],
) -> T:
    """Open a UoW, run Domain work, commit, then dispatch events."""
    with uow_factory() as uow:
        try:
            result, events = work(uow)
            commit_and_dispatch(uow, dispatcher, events)
            return result
        except DomainError as exc:
            uow.rollback()
            raise translate_domain_error(exc) from exc
        except Exception:
            uow.rollback()
            raise


def with_domain_errors[T](fn: Callable[[], T]) -> T:
    try:
        return fn()
    except DomainError as exc:
        raise translate_domain_error(exc) from exc


def replay_or_begin[T](
    store: IdempotencyStore | None,
    *,
    key: str | None,
    scope: str,
    actor: Actor,
    rebuild: Callable[[dict[str, Any]], T],
) -> T | None:
    """Return a rebuilt prior result if the idempotency key completed; else None."""
    if store is None or key is None:
        return None
    scoped = f"{scope}:{actor.id}"
    existing = store.get(key=key, scope=scoped)
    if existing is None:
        return None
    if existing.status is IdempotencyStatus.COMPLETED and existing.result is not None:
        return rebuild(existing.result)
    raise ConflictError(
        "Idempotency key is already in use without a completed result",
        code="IDEMPOTENCY_IN_PROGRESS",
        details={"key": key, "scope": scoped},
    )


def store_idempotent_result(
    store: IdempotencyStore | None,
    *,
    key: str | None,
    scope: str,
    actor: Actor,
    result: object,
) -> None:
    if store is None or key is None:
        return
    scoped = f"{scope}:{actor.id}"
    store.put_completed(
        key=key,
        scope=scoped,
        result=dto_to_idempotency_payload(result),
    )
