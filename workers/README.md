# agent-eval-workers

Background Workers and Execution Runtime for EvalForge.

## Why

Per Backend Architecture §4 / §7 and the Execution Engine Architecture,
Workers are the **thin chassis** for asynchronous evaluation: they claim
queued Runs, host the Execution Engine, and sequence Application calls that
advance Run lifecycle. They do not contain Adapter translation or Grader
judgment.

## Rules

| Owns                                                         | Must NOT do                            |
| ------------------------------------------------------------ | -------------------------------------- |
| Queue consumption / claim hosting                            | Adapter vendor translation             |
| Hosting Execution Engine orchestration                       | Grader scoring / rubric judgment       |
| Sequencing Application use cases for Run status              | Bypass Application for business writes |
| Checkpoints, cancellation hooks, event pipeline wiring       | Talk to the API Layer                  |
| Failure classification into Application-mediated transitions | Domain invariants (Domain owns those)  |

**Allowed dependencies (target):** `application`, `domain`, `shared`, and
(at composition) `infrastructure`, plus Adapter/Grader **ports** invoked by
the Engine — never API.

## Package layout

```
agent_eval_workers/
  worker/              # Process chassis — claim host, Engine entry
  execution_engine/    # Orchestration authority for one Run
  scheduler/           # Queue → worker delivery policy
  lifecycle/           # Named Run stages / transition contracts
  cancellation/        # Cooperative cancel propagation
  checkpoints/         # Crash-recovery progress markers
  event_pipeline/      # Event/Artifact stream → persistence
```

## Status

**Phase 2 — Run lifecycle orchestration** is implemented under `lifecycle/`:

- Explicit `OrchestrationPhase` state machine with validated transitions
- Failure / cancel / timeout paths (orchestration only)
- Ports for Sandbox, Adapter, event pipeline, grading schedule, status projection
- Domain `RunStatus` mapping (Engine phases project onto Domain; Domain owns invariants)

Still deferred: claim loop, concrete Adapter/Sandbox/Grader wiring, event
pipeline persistence, checkpoints, cancellation propagation.

## Lifecycle (Phase 2)

Happy path:

`Queued → Claimed → Sandbox Provisioning → Sandbox Ready → Adapter Starting →
Execution Streaming → Adapter Finished → Final Event Persistence →
Grading Scheduled → Completed`

Terminal failure/cancel phases: `Failed`, `Cancelled`.

Illegal transitions raise `IllegalLifecycleTransition` immediately.

## Boundaries (authoritative)

- **Execution Engine** owns orchestration, retries coordination, lifecycle
  steps, checkpoints usage, and grader _scheduling_.
- **Adapter** owns translation to the Normalized Domain Model.
- **Grader** owns scoring.
- **Application** owns authorization, UoW commit boundaries, and Domain
  status transitions invoked by the runtime.
- **Infrastructure** owns concrete queue / DB / object storage adapters.
- **Lifecycle** owns sequencing and transition validation only — never
  Adapter translation, grading, direct persistence, or direct enqueue.
