"""Platform catalog domain invariants."""

from __future__ import annotations

import pytest
from agent_eval_domain.common.errors import InvariantViolation
from agent_eval_domain.common.ids import PlatformId, PlatformVersionId
from agent_eval_domain.platform.platform import Platform
from agent_eval_domain.versioning.status import VersionStatus


def _draft(**policy_overrides):
    platform = Platform.create(platform_id=PlatformId("platform-1"), name="Linux")
    policies = {
        "sandbox_policy": {"network_mode": "isolated"},
        "execution_policy": {"runner": "docker"},
        "timeout_policy": {"default_timeout_seconds": "60"},
        "environment_policy": {"allowlist_ref": "default"},
        "grading_policy": {"mode": "deterministic"},
    }
    policies.update(policy_overrides)
    version = platform.create_draft_version(
        version_id=PlatformVersionId("platform-version-1"),
        label="Linux v1",
        **policies,
    )
    return platform, version


def test_platform_policies_are_immutable() -> None:
    _, version = _draft()
    with pytest.raises(TypeError):
        version.sandbox_policy["network_mode"] = "host"  # type: ignore[index]


def test_only_active_and_superseded_versions_are_pinnable() -> None:
    platform, draft = _draft()
    assert draft.status is VersionStatus.DRAFT
    assert not draft.is_pinnable()
    active = platform.publish_version(draft.id)
    assert active.is_pinnable()
    next_draft = platform.create_draft_version(
        version_id=PlatformVersionId("platform-version-2"),
        label="Linux v2",
        sandbox_policy={},
        execution_policy={},
        timeout_policy={},
        environment_policy={},
        grading_policy={},
    )
    platform.publish_version(next_draft.id)
    assert platform.get_version(active.id).status is VersionStatus.SUPERSEDED
    assert platform.get_version(active.id).is_pinnable()


@pytest.mark.parametrize(
    "policy",
    [
        {"api_key": "value"},
        {"credential": "sk-live-secret"},
        {"password_ref": "vault"},
        {"key": "access_token"},
    ],
)
def test_platform_policy_rejects_secret_like_material(
    policy: dict[str, str],
) -> None:
    with pytest.raises(InvariantViolation, match="secret-like"):
        _draft(environment_policy=policy)


def test_platform_policy_rejects_non_string_values() -> None:
    with pytest.raises(InvariantViolation, match="only string"):
        _draft(execution_policy={"retries": 3})  # type: ignore[dict-item]
