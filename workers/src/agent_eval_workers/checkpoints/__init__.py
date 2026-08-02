"""Checkpoints — durable progress markers for crash recovery.

Responsibility (Execution Engine Architecture — worker crash / retry safety):
- Record how far orchestration has progressed for a claimed Run
- Allow a replacement worker to resume without duplicating completed steps
- Align with Infrastructure idempotency / lease semantics for redelivery

Must NOT:
- Replace Domain append-only event history
- Store Adapter vendor state
- Decide business outcomes (Engine lifecycle still decides next step)

Phase 1: structure only — no checkpoint persistence.
"""
