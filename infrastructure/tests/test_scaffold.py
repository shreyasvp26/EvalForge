"""Scaffold smoke test — package import graph is wired."""

from __future__ import annotations

import agent_eval_infrastructure


def test_infrastructure_package_importable() -> None:
    assert agent_eval_infrastructure.__doc__ is not None
