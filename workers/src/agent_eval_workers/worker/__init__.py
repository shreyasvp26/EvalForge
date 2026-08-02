"""Worker process chassis — queue claim host and Engine invocation boundary.

Responsibility (Execution Engine Architecture / Backend Architecture §4):
- Consume Run tasks from the Application/Infrastructure queue contract
- Provide a running process for the Execution Engine's orchestration
- Sequence Application use cases that advance Run lifecycle state
- Attach correlation / run / worker identifiers for observability
- Translate process-level failures into Application-mediated lifecycle outcomes

Must NOT:
- Decide what step a Run takes next (Execution Engine owns orchestration)
- Contain Adapter translation or Grader scoring logic
- Talk to the API Layer
- Bypass Application to write business state directly to Infrastructure
- Persist Execution Events / Artifacts itself (event pipeline + Application)

Phase 1: structure only — no claim loop or business behavior.
"""
