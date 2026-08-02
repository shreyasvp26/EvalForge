from __future__ import annotations

import pytest
from agent_eval_domain.common.errors import InvalidStateTransition
from agent_eval_domain.versioning.status import VersionStatus, assert_version_transition


def test_version_draft_to_active() -> None:
    assert_version_transition(
        entity="CaseVersion",
        current=VersionStatus.DRAFT,
        target=VersionStatus.ACTIVE,
    )


def test_version_active_to_superseded_and_retired() -> None:
    assert_version_transition(
        entity="CaseVersion",
        current=VersionStatus.ACTIVE,
        target=VersionStatus.SUPERSEDED,
    )
    assert_version_transition(
        entity="CaseVersion",
        current=VersionStatus.ACTIVE,
        target=VersionStatus.RETIRED,
    )


def test_version_terminal_states_are_closed() -> None:
    with pytest.raises(InvalidStateTransition):
        assert_version_transition(
            entity="CaseVersion",
            current=VersionStatus.SUPERSEDED,
            target=VersionStatus.ACTIVE,
        )
    with pytest.raises(InvalidStateTransition):
        assert_version_transition(
            entity="CaseVersion",
            current=VersionStatus.RETIRED,
            target=VersionStatus.ACTIVE,
        )
