"""Scheduler — delivery policy between queue and worker pickup.

Responsibility (Execution Engine Architecture — Scheduling step):
- Express how queued Runs become eligible for worker claim
  (ordering, fairness, resource-class routing — platform policy)
- Remain separate from orchestration workflow inside the Engine

Must NOT:
- Advance Run Domain status (Application / Engine lifecycle)
- Invoke Adapters or Graders
- Implement broker internals (Infrastructure queue adapters)

Phase 1: structure only — no scheduling policy.
"""
