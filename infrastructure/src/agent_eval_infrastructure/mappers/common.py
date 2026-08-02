"""Shared mapper helpers."""

from __future__ import annotations

from uuid import NAMESPACE_URL, uuid5

from agent_eval_domain.common.errors import NotFoundError
from agent_eval_domain.versioning.models import VersionNumber
from agent_eval_domain.versioning.status import EntityAdminStatus, VersionStatus


def require_found[T](entity: T | None, *, entity_type: str, entity_id: str) -> T:
    if entity is None:
        raise NotFoundError(
            f"{entity_type} not found",
            entity=entity_type,
            entity_id=entity_id,
        )
    return entity


def parse_admin_status(value: str) -> EntityAdminStatus:
    return EntityAdminStatus(value)


def parse_version_status(value: str) -> VersionStatus:
    return VersionStatus(value)


def parse_version_number(value: int) -> VersionNumber:
    return VersionNumber(value)


def deterministic_id(*parts: str) -> str:
    """Stable opaque id for association rows (fits String(64) PK columns)."""
    return str(uuid5(NAMESPACE_URL, ":".join(parts)))
