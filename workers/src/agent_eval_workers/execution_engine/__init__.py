"""Execution Engine — orchestration authority for a single Run.

Responsibility (Execution Engine Architecture):
- Own the step sequence from worker pickup through terminal completion
- Decide when a Sandbox is provisioned and torn down
- Invoke exactly one Adapter per Run (via Adapter port — not vendor code)
- Ensure Execution Events and Artifacts are durably recorded before a step
  is considered complete
- Schedule / isolate Grader invocations after execution closes
  (scheduling only — Graders own judgment)
- Detect and classify failure modes along the Run path

Must NOT:
- Contain vendor-specific translation (Adapter Layer)
- Contain scoring / rubric judgment (Grader Layer)
- Talk to PostgreSQL, object storage, or the queue directly
  (Application + Infrastructure contracts only)
- Own authorization or API-facing concerns
- Own the Sandbox compute substrate mechanics

Phase 1: structure only — no lifecycle behavior.
"""
