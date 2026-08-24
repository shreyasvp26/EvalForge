"""Idempotency payload serialization — datetime and nested DTO safety."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from enum import Enum
from uuid import UUID

import pytest
from agent_eval_application.commands.project import CreateProjectCommand
from agent_eval_application.common.actor import Actor
from agent_eval_application.dto.project import ProjectDTO
from agent_eval_application.use_cases.base import (
    dto_to_idempotency_payload,
    json_safe_idempotency_value,
)
from agent_eval_application.use_cases.project import CreateProject
from agent_eval_domain.common.ids import ProjectId
from fakes import (
    AllowAllAuth,
    InMemoryIdempotencyStore,
    InMemoryIdGenerator,
    InMemoryUnitOfWorkFactory,
    RecordingEventDispatcher,
    SharedStore,
)


class Color(Enum):
    RED = "red"


@dataclass(frozen=True, slots=True)
class NestedDTO:
    label: str
    when: datetime


@dataclass(frozen=True, slots=True)
class SampleDTO:
    id: str
    created_at: datetime
    day: date
    uid: UUID
    color: Color
    nested: NestedDTO
    tags: list[str]
    meta: dict[str, str]
    optional: str | None


def test_dto_with_datetime_is_json_serializable() -> None:
    dto = SampleDTO(
        id="p1",
        created_at=datetime(2026, 8, 24, 12, 0, tzinfo=UTC),
        day=date(2026, 8, 24),
        uid=UUID("12345678-1234-5678-1234-567812345678"),
        color=Color.RED,
        nested=NestedDTO(label="n", when=datetime(2026, 1, 1, tzinfo=UTC)),
        tags=["a", "b"],
        meta={"k": "v"},
        optional=None,
    )
    payload = dto_to_idempotency_payload(dto)
    encoded = json.dumps(payload)
    decoded = json.loads(encoded)
    assert decoded["created_at"] == "2026-08-24T12:00:00+00:00"
    assert decoded["day"] == "2026-08-24"
    assert decoded["uid"] == "12345678-1234-5678-1234-567812345678"
    assert decoded["color"] == "red"
    assert decoded["nested"]["when"] == "2026-01-01T00:00:00+00:00"
    assert decoded["optional"] is None


def test_project_dto_payload_is_json_serializable() -> None:
    dto = ProjectDTO(
        id="proj-1",
        name="Alpha",
        description="d",
        status="active",
        created_at=datetime(2026, 8, 24, 15, 30, tzinfo=UTC),
        settings={"k": "v"},
    )
    payload = dto_to_idempotency_payload(dto)
    assert json.loads(json.dumps(payload))["created_at"] == "2026-08-24T15:30:00+00:00"


def test_create_project_idempotent_with_datetime_dto() -> None:
    store = SharedStore()
    auth = AllowAllAuth()
    idempotency = InMemoryIdempotencyStore()
    uc = CreateProject(
        InMemoryUnitOfWorkFactory(store),
        InMemoryIdGenerator("proj"),
        auth,
        RecordingEventDispatcher(),
        idempotency,
    )
    cmd = CreateProjectCommand(
        actor=Actor(id="user-1"),
        name="Alpha",
        description="d",
        idempotency_key="ik-datetime",
    )
    first = uc.execute(cmd)
    second = uc.execute(cmd)
    assert first.id == second.id
    assert first.created_at == second.created_at
    assert len(store.projects.list_all()) == 1
    assert auth.granted_owners == [("user-1", first.id)]
    scoped = idempotency.get(key="ik-datetime", scope="create_project:user-1")
    assert scoped is not None
    assert scoped.result is not None
    json.dumps(scoped.result)
    # Original DB record remains valid / readable.
    loaded = store.projects.get(ProjectId(first.id))
    assert loaded.name == "Alpha"


def test_json_safe_rejects_unknown_types() -> None:
    with pytest.raises(TypeError, match="Cannot serialize"):
        json_safe_idempotency_value(object())
