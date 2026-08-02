"""Lifecycle — Run step machine hosted by the Execution Engine.

Responsibility (Execution Engine Architecture — Run Lifecycle):
- Model the named orchestration stages (queueing → sandbox → adapter →
  streaming → grading schedule → terminal states)
- Encode allowed transitions and failure-path entry points as orchestration
  contracts (interfaces), not Domain aggregate mutations
- Coordinate with Application use cases that perform the actual status
  transitions on the EvaluationRun aggregate

Must NOT:
- Re-implement Domain RunStatus invariants (Domain owns those)
- Embed Adapter or Grader logic
- Persist state outside Application / Infrastructure contracts

Phase 1: structure only — no transition implementation.
"""
