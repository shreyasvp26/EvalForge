"""Router registration for the Control Plane foundation (Phase 6A)."""

from agent_eval_api.routers import health, system, v1_root

__all__ = ["health", "system", "v1_root"]
