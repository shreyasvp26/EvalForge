"""Platform aggregate and immutable platform configuration versions."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from datetime import datetime

from agent_eval_domain.common.aggregate import AggregateRoot
from agent_eval_domain.common.errors import InvariantViolation
from agent_eval_domain.common.events import utc_now
from agent_eval_domain.common.ids import PlatformId, PlatformVersionId
from agent_eval_domain.versioning.models import VersionNumber
from agent_eval_domain.versioning.status import (
    EntityAdminStatus,
    VersionStatus,
    assert_version_transition,
)

_SECRET_MARKERS = (
    "api_key",
    "apikey",
    "password",
    "passwd",
    "secret",
    "access_token",
    "auth_token",
    "private_key",
    "sk-",
)


class _FrozenPolicy(dict[str, str]):
    """Small JSON-compatible immutable dictionary."""

    def _immutable(self, *args: object, **kwargs: object) -> None:
        raise TypeError("Platform policies are immutable")

    __setitem__ = _immutable
    __delitem__ = _immutable
    clear = _immutable
    pop = _immutable
    popitem = _immutable
    setdefault = _immutable
    update = _immutable

    def __deepcopy__(self, memo: dict[int, object]) -> _FrozenPolicy:
        return self


def _sanitize_policy(value: object, *, field_name: str) -> Mapping[str, str]:
    if not isinstance(value, Mapping):
        raise InvariantViolation(
            f"{field_name} must be a string dictionary",
            code="INVALID_PLATFORM_POLICY",
            details={"field": field_name},
        )
    sanitized: dict[str, str] = {}
    for key, item in value.items():
        if not isinstance(key, str) or not isinstance(item, str):
            raise InvariantViolation(
                f"{field_name} must contain only string keys and values",
                code="INVALID_PLATFORM_POLICY",
                details={"field": field_name},
            )
        searchable = f"{key} {item}".lower()
        if any(marker in searchable for marker in _SECRET_MARKERS):
            raise InvariantViolation(
                f"{field_name} contains secret-like material",
                code="SECRET_IN_PLATFORM_POLICY",
                details={"field": field_name, "key": key},
            )
        sanitized[key] = item
    return _FrozenPolicy(sanitized)


@dataclass(frozen=True, slots=True)
class PlatformVersion:
    id: PlatformVersionId
    platform_id: PlatformId
    version_number: VersionNumber
    status: VersionStatus
    label: str
    sandbox_policy: Mapping[str, str]
    execution_policy: Mapping[str, str]
    timeout_policy: Mapping[str, str]
    environment_policy: Mapping[str, str]
    grading_policy: Mapping[str, str]
    notes: str = ""
    predecessor_version_id: PlatformVersionId | None = None
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        label = self.label.strip()
        if not label:
            raise InvariantViolation(
                "Platform Version label must be non-empty",
                code="INVALID_PLATFORM_VERSION_LABEL",
            )
        object.__setattr__(self, "label", label)
        for field_name in (
            "sandbox_policy",
            "execution_policy",
            "timeout_policy",
            "environment_policy",
            "grading_policy",
        ):
            object.__setattr__(
                self,
                field_name,
                _sanitize_policy(getattr(self, field_name), field_name=field_name),
            )

    def is_pinnable(self) -> bool:
        return self.status in {VersionStatus.ACTIVE, VersionStatus.SUPERSEDED}


@dataclass(slots=True)
class Platform(AggregateRoot):
    id: PlatformId
    name: str
    status: EntityAdminStatus = EntityAdminStatus.ACTIVE
    created_at: datetime = field(default_factory=utc_now)
    _versions: list[PlatformVersion] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        AggregateRoot.__init__(self)
        if not self.name.strip():
            raise InvariantViolation(
                "Platform name must be non-empty",
                code="INVALID_PLATFORM_NAME",
            )
        self.name = self.name.strip()

    @classmethod
    def create(cls, *, platform_id: PlatformId, name: str) -> Platform:
        return cls(id=platform_id, name=name)

    @property
    def versions(self) -> tuple[PlatformVersion, ...]:
        return tuple(self._versions)

    def active_version(self) -> PlatformVersion | None:
        return next(
            (v for v in reversed(self._versions) if v.status is VersionStatus.ACTIVE),
            None,
        )

    def get_version(self, version_id: PlatformVersionId) -> PlatformVersion:
        for version in self._versions:
            if version.id == version_id:
                return version
        raise InvariantViolation(
            f"Platform version {version_id} not found",
            code="PLATFORM_VERSION_NOT_FOUND",
            details={"platform_id": self.id.value, "version_id": version_id.value},
        )

    def create_draft_version(
        self,
        *,
        version_id: PlatformVersionId,
        label: str,
        sandbox_policy: dict[str, str],
        execution_policy: dict[str, str],
        timeout_policy: dict[str, str],
        environment_policy: dict[str, str],
        grading_policy: dict[str, str],
        notes: str = "",
        created_at: datetime | None = None,
    ) -> PlatformVersion:
        predecessor = self.active_version()
        version = PlatformVersion(
            id=version_id,
            platform_id=self.id,
            version_number=(
                VersionNumber(1)
                if predecessor is None
                else predecessor.version_number.next()
            ),
            status=VersionStatus.DRAFT,
            label=label,
            sandbox_policy=sandbox_policy,
            execution_policy=execution_policy,
            timeout_policy=timeout_policy,
            environment_policy=environment_policy,
            grading_policy=grading_policy,
            notes=notes,
            predecessor_version_id=predecessor.id if predecessor else None,
            created_at=created_at or utc_now(),
        )
        self._versions.append(version)
        return version

    def publish_version(self, version_id: PlatformVersionId) -> PlatformVersion:
        draft = self.get_version(version_id)
        assert_version_transition(
            entity="PlatformVersion",
            current=draft.status,
            target=VersionStatus.ACTIVE,
        )
        current = self.active_version()
        if current is not None and current.id != draft.id:
            self._replace(current, replace(current, status=VersionStatus.SUPERSEDED))
        published = replace(draft, status=VersionStatus.ACTIVE)
        self._replace(draft, published)
        return published

    def _replace(self, old: PlatformVersion, new: PlatformVersion) -> None:
        self._versions[self._versions.index(old)] = new
