"""Compatibility re-export — FakeDockerEngine lives in the sandbox package."""

from __future__ import annotations

from agent_eval_sandbox.docker.fake import FakeContainer, FakeDockerEngine

__all__ = ["FakeContainer", "FakeDockerEngine"]
