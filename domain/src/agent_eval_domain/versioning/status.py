"""Version lifecycle shared by Suite, Case, Prompt, Grader (and identity status)."""

from __future__ import annotations

from enum import StrEnum

from agent_eval_domain.common.errors import InvalidStateTransition


class VersionStatus(StrEnum):
    """Lifecycle of an independently addressable Version (Domain Model §7)."""

    DRAFT = "draft"
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    RETIRED = "retired"


_VERSION_TRANSITIONS: dict[VersionStatus, frozenset[VersionStatus]] = {
    VersionStatus.DRAFT: frozenset({VersionStatus.ACTIVE}),
    VersionStatus.ACTIVE: frozenset({VersionStatus.SUPERSEDED, VersionStatus.RETIRED}),
    VersionStatus.SUPERSEDED: frozenset(),
    VersionStatus.RETIRED: frozenset(),
}


def assert_version_transition(
    *,
    entity: str,
    current: VersionStatus,
    target: VersionStatus,
) -> None:
    allowed = _VERSION_TRANSITIONS[current]
    if target not in allowed:
        raise InvalidStateTransition(
            f"{entity} cannot transition from {current} to {target}",
            from_state=current.value,
            to_state=target.value,
            entity=entity,
        )


class EntityAdminStatus(StrEnum):
    """Administrative status of a stable identity (Suite, Case, Agent, …)."""

    ACTIVE = "active"
    DEPRECATED = "deprecated"
