"""Event pipeline — Execution Event / Artifact streaming into persistence.

Responsibility (Execution Engine Architecture — continuous recording):
- Accept Normalized Domain Model actions streamed from the Adapter port
- Assign strict sequence numbers within a Run
- Route oversized payloads to object storage (via Infrastructure storage)
- Persist Execution Events and Artifact metadata through Application /
  Infrastructure contracts in append-only order
- Expose an event-publication interface for later observers (not SSE/API)

Must NOT:
- Translate vendor-native actions (Adapter owns translation)
- Grade or interpret events (Grader owns scoring)
- Implement SSE or HTTP streaming (API Layer)
- Commit transactions itself if Application UoW owns the boundary

Phase 1: structure only — no streaming or persistence behavior.
"""
