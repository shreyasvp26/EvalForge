"""Strongly typed entity identifiers.

IDs are opaque strings at the Domain Layer. Generation strategy (UUID, ULID, …)
is an Application/Infrastructure concern; Domain only requires non-empty identity.
"""

from __future__ import annotations

from dataclasses import dataclass

from agent_eval_domain.common.errors import InvariantViolation


def _require_non_empty(value: str, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvariantViolation(
            f"{field} must be a non-empty string",
            code="INVALID_ID",
            details={"field": field},
        )
    return value.strip()


@dataclass(frozen=True, slots=True)
class EntityId:
    """Base typed identifier."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _require_non_empty(self.value, field="id"))

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class ProjectId(EntityId):
    pass


@dataclass(frozen=True, slots=True)
class SuiteId(EntityId):
    pass


@dataclass(frozen=True, slots=True)
class SuiteVersionId(EntityId):
    pass


@dataclass(frozen=True, slots=True)
class CaseId(EntityId):
    pass


@dataclass(frozen=True, slots=True)
class CaseVersionId(EntityId):
    pass


@dataclass(frozen=True, slots=True)
class PromptId(EntityId):
    pass


@dataclass(frozen=True, slots=True)
class PromptVersionId(EntityId):
    pass


@dataclass(frozen=True, slots=True)
class AgentId(EntityId):
    pass


@dataclass(frozen=True, slots=True)
class AgentVersionId(EntityId):
    pass


@dataclass(frozen=True, slots=True)
class AdapterId(EntityId):
    pass


@dataclass(frozen=True, slots=True)
class AdapterVersionId(EntityId):
    pass


@dataclass(frozen=True, slots=True)
class GraderId(EntityId):
    pass


@dataclass(frozen=True, slots=True)
class GraderVersionId(EntityId):
    pass


@dataclass(frozen=True, slots=True)
class RunId(EntityId):
    pass


@dataclass(frozen=True, slots=True)
class ExecutionEventId(EntityId):
    pass


@dataclass(frozen=True, slots=True)
class ArtifactId(EntityId):
    pass


@dataclass(frozen=True, slots=True)
class ScoreId(EntityId):
    pass


@dataclass(frozen=True, slots=True)
class SandboxId(EntityId):
    pass


@dataclass(frozen=True, slots=True)
class PlatformVersionId(EntityId):
    """Platform Version recorded on every Run (seventh versioning axis)."""

    pass
