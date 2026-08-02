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
| Retry policy / lease ack-release                             | Domain invariants (Domain owns those)  |
| Failure classification into Application-mediated transitions | Mutate Domain Run status directly      |

**Allowed dependencies (target):** `application`, `domain`, `shared`, and
(at composition) `infrastructure`, plus Adapter/Grader **ports** invoked by
the Engine — never API.

## Package layout

```
agent_eval_workers/
  worker/              # Process chassis — claim, retry, heartbeat, shutdown
  execution_engine/    # Orchestration authority for one Run
  scheduler/           # Queue → worker delivery policy (Phase 1 scaffold)
  lifecycle/           # Named Run stages / transition contracts
  cancellation/        # Cooperative cancel observation
  checkpoints/         # Crash-recovery progress markers
  event_pipeline/      # Durable Event/Artifact recording + projection hooks
  clock.py             # Monotonic clock port (timeouts)
```

## Status

**Phases 2–4** are implemented (lifecycle, worker runtime, event pipeline).

**Phase 4 — Event persistence pipeline:**

- `EventPersistencePipeline` — ordered buffer, Application-mediated writes,
  batching, `persist_final` (lifecycle port)
- Application `RecordExecutionEvent` + idempotent `RecordArtifact`
- Domain idempotent replay by event/artifact id (append-only, no mutate)
- `EventProjector` / `ProjectionHub` hooks for future SSE/WebSocket consumers
- `PersistenceFailure` classified for Worker retry policy

Still deferred: concrete Adapter/Sandbox/Grader wiring, scheduler delivery
policy, Redis-backed worker queue adapter, live SSE networking.

## Event pipeline (Phase 4)

```
Engine emits NDM actions / artifacts
        ↓
EventPersistencePipeline (ordered buffer, optional batch)
        ↓
Application RecordArtifact / RecordExecutionEvent
        ↓
Domain EvaluationRun append-only history
        ↓
ProjectionHub → EventProjector subscribers (no networking yet)
```

Rules: never bypass Application; never mutate past events; duplicates are
safe; flush stops on first failure without skipping remaining items.

## Lifecycle (Phase 2)

Happy path:

`Queued → Claimed → Sandbox Provisioning → Sandbox Ready → Adapter Starting →
Execution Streaming → Adapter Finished → Final Event Persistence →
Grading Scheduled → Completed`

Terminal failure/cancel phases: `Failed`, `Cancelled`.

Illegal transitions raise `IllegalLifecycleTransition` immediately.

## Worker vs Engine

| Concern                   | Owner                                           |
| ------------------------- | ----------------------------------------------- |
| Next lifecycle step       | Execution Engine                                |
| Queue lease / ack         | Worker                                          |
| Retry budget              | Worker                                          |
| Cancel observation        | Worker ports → Engine applies `CANCEL`          |
| Execution timeout         | Engine (propagates `TIMEOUT`)                   |
| Checkpoint create/restore | Engine writes; Worker restores on claim         |
| Domain Run status         | Lifecycle → status port (never Worker directly) |

## Boundaries (authoritative)

- **Execution Engine** owns orchestration, lifecycle steps, checkpoint
  writes during execution, and grader _scheduling_.
- **Worker** owns queue leases, retry policy, heartbeats, process shutdown.
- **Adapter** owns translation to the Normalized Domain Model.
- **Grader** owns scoring.
- **Application** owns authorization, UoW commit boundaries, and Domain
  status transitions invoked by the runtime.
- **Infrastructure** owns concrete queue / DB / object storage adapters.
- **Lifecycle** owns sequencing and transition validation only — never
  Adapter translation, grading, direct persistence, or direct enqueue.
