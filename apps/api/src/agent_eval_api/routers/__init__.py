"""Router registration for the Control Plane."""

from agent_eval_api.routers import health, metrics, system, v1_root
from agent_eval_api.routers.v1 import (
    adapters,
    agents,
    cases,
    graders,
    projects,
    prompts,
    runs,
    suites,
)

__all__ = [
    "adapters",
    "agents",
    "cases",
    "graders",
    "health",
    "metrics",
    "projects",
    "prompts",
    "runs",
    "suites",
    "system",
    "v1_root",
]
