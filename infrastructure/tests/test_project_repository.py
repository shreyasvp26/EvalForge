"""Project repository adapter tests."""

from __future__ import annotations

import pytest
from agent_eval_domain.common.errors import NotFoundError
from agent_eval_domain.common.ids import ProjectId
from agent_eval_domain.versioning.status import EntityAdminStatus

from .conftest import seed_project


def test_project_save_get_update(repos) -> None:
    project = seed_project(repos)
    loaded = repos["projects"].get(project.id)
    assert loaded.name == "Demo"
    assert loaded.settings == {"region": "us"}

    loaded.name = "Renamed"
    loaded.status = EntityAdminStatus.DEPRECATED
    loaded.settings["tier"] = "pro"
    repos["projects"].save(loaded)
    repos["session"].flush()

    again = repos["projects"].get(project.id)
    assert again.name == "Renamed"
    assert again.status is EntityAdminStatus.DEPRECATED
    assert again.settings["tier"] == "pro"


def test_project_get_missing(repos) -> None:
    with pytest.raises(NotFoundError):
        repos["projects"].get(ProjectId("missing"))
