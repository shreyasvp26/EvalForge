"""Cancellation — cooperative stop signals for in-flight Runs.

Responsibility (Execution Engine Architecture — cancellation / terminal paths):
- Observe cancellation requests for a claimed Run
- Propagate cancellation into Engine lifecycle so Sandbox / Adapter work
  stops cleanly and the Run reaches ``Cancelled`` via Application
- Distinguish cancellation from infrastructure failure and Agent task failure

Must NOT:
- Silently drop Execution Events already recorded
- Bypass Application when recording the terminal Cancelled transition
- Own Adapter-internal interrupt mechanisms (Adapter port may expose a hook)

Phase 1: structure only — no cancellation handling.
"""
