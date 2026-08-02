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
  execution_engine/    # Orchestration authority + Phase 5 composition harness
  scheduler/           # Queue → worker delivery policy (scaffold)
  lifecycle/           # Named Run stages / transition contracts
  cancellation/        # Cooperative cancel observation
  checkpoints/         # Crash-recovery progress markers
  event_pipeline/      # Durable Event/Artifact recording + projection hooks
  mocks/               # Deterministic Sandbox / Adapter / Grader stubs
  clock.py             # Monotonic clock port (timeouts)
```

## Status

**Phases 2–5** are implemented. Phase 5 wires the complete mocked end-to-end
orchestration path via `build_orchestration_harness()`.

Still deferred: real Adapter/Sandbox/Grader packages, scheduler delivery
policy, Redis worker-queue adapter, live SSE networking.

## Complete orchestration sequence (Phase 5)

```
Queue claim (Worker)
        ↓
Checkpoint restore (Worker)
        ↓
ExecutionEngine.execute
        ↓
Lifecycle: CLAIM → status.project_running
        ↓
BEGIN_SANDBOX_PROVISIONING → MockSandbox.provision
        ↓
SANDBOX_READY
        ↓
START_ADAPTER → MockAdapter.start
        ↓
ADAPTER_STARTED → MockAdapter.run  (streams events/artifacts continuously
                                     into EventPersistencePipeline)
        ↓
ADAPTER_FINISHED → MockAdapter.finish
        ↓
PERSIST_FINAL_EVENTS → pipeline.persist_final
        ↓
FINALS_PERSISTED → MockGradingScheduler.schedule (isolated MockGraders)
                 → status.project_grading
        ↓
GRADING_FINISHED → status.project_completed
        ↓
Worker ack
```

Use `agent_eval_workers.execution_engine.build_orchestration_harness` for
deterministic verification without Redis, Postgres, S3, or vendor code.

## Event pipeline (Phase 4)

```
Adapter emits NDM actions / artifacts (continuously during run)
        ↓
EventPersistencePipeline (ordered buffer, optional batch)
        ↓
Application RecordArtifact / RecordExecutionEvent
        ↓
Domain EvaluationRun append-only history
        ↓
ProjectionHub → EventProjector subscribers (no networking yet)
```

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
| Event streaming           | Adapter → Event Pipeline (Engine sequences)     |
| Grader judgment           | Grader (Engine only schedules)                  |

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
- The Engine never knows Redis, SQLAlchemy, repositories, S3, or queue
  implementation details — only ports.
