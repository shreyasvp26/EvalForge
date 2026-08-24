"""Redis idempotency store accepts JSON-safe datetime payloads."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from agent_eval_application.dto.project import ProjectDTO
from agent_eval_application.use_cases.base import dto_to_idempotency_payload
from agent_eval_infrastructure.idempotency.redis_store import RedisIdempotencyStore

from .fakes import FakeRedis


def test_redis_idempotency_stores_project_dto_with_datetime() -> None:
    dto = ProjectDTO(
        id="proj-1",
        name="Alpha",
        description="d",
        status="active",
        created_at=datetime(2026, 8, 24, 15, 30, tzinfo=UTC),
        settings={"k": "v"},
    )
    payload = dto_to_idempotency_payload(dto)
    store = RedisIdempotencyStore(FakeRedis(), key_prefix="test:idemp")
    store.put_completed(key="ik-1", scope="create_project:user-1", result=payload)
    record = store.get(key="ik-1", scope="create_project:user-1")
    assert record is not None
    assert record.result is not None
    assert record.result["created_at"] == "2026-08-24T15:30:00+00:00"
    json.dumps(record.result)
