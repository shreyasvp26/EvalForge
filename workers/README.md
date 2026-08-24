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

**Allowed dependencies:** `application`, `domain`, `shared`, and (at
composition) `sandbox`, `adapters`, `graders`, plus Infrastructure ports —
never API.

## Package layout

```
agent_eval_workers/
  worker/              # Process chassis — claim, retry, heartbeat, shutdown
  execution_engine/    # Orchestration authority + Phase 5 mock harness
  integration/         # Phase 11 production bridges (Sandbox/Adapter/Graders)
  scheduler/           # Queue → worker delivery policy (scaffold)
  lifecycle/           # Named Run stages / transition contracts
  cancellation/        # Cooperative cancel observation
  checkpoints/         # Crash-recovery progress markers
  event_pipeline/      # Durable Event/Artifact recording + projection hooks
  mocks/               # Deterministic stubs (Phase 5 harness only)
  clock.py             # Monotonic clock port (timeouts)
```

## Status

**Phases 2–5** — mocked end-to-end orchestration via
`build_orchestration_harness()`.

**Phase 11** — production pipeline via `build_production_harness()`:

Worker → Execution Engine → Docker Sandbox → Claude Code Adapter →
Event Persistence → Objective + Rubric Graders → Application scores →
Run Completed.

**Phase 2 process wiring** — `evalforge-worker` uses
`build_production_worker()` so Redis claims execute the production
LifecycleOrchestrator against SQLAlchemy UoW, MinIO artifact bytes, and
Redis cancel signals.

| Env                            | Compose default                    | Notes                                                         |
| ------------------------------ | ---------------------------------- | ------------------------------------------------------------- |
| `WORKER_SANDBOX_ENGINE`        | `docker`                           | Real `DockerPyEngine` via socket; use `fake`/`auto` for tests |
| `WORKER_ADAPTER_MODE`          | `deterministic`                    | Injected Claude NDJSON; set `claude` for live CLI             |
| `WORKER_SANDBOX_IMAGE`         | `evalforge/sandbox:local`          | Built by Compose `sandbox-image`                              |
| `WORKER_SANDBOX_NETWORK`       | `none`                             | Use `bridge` for live Claude egress                           |
| `WORKER_SANDBOX_ENV_ALLOWLIST` | `ANTHROPIC_API_KEY,PATH,HOME,TERM` | Never pass full host env                                      |
| `WORKER_SANDBOX_VERIFY`        | `0`                                | Opt-in post-provision workspace exec (`true`)                 |
| `WORKER_ACTOR_ID`              | `system-worker`                    | Trusted worker Actor                                          |

```bash
uv run evalforge-worker
uv run pytest workers/tests/test_process_worker.py
uv run pytest workers/tests -m "not integration"
# Live DockerSandbox e2e (optional; Compose + sandbox/tests cover the path):
EVALFORGE_LIVE_WORKER_DOCKER=1 uv run pytest workers/tests/test_docker_production_integration.py -m integration
```

Still deferred: live SSE networking, richer pin→adapter registry, frontend redesign.

Live Claude provider execution requires credentials + CLI in the sandbox image;
without them, DockerSandbox + deterministic adapter remain the verified path.

## Production execution pipeline (Phase 11)

```
Queue claim (Worker)
        ↓
Checkpoint restore (Worker)
        ↓
ExecutionEngine.execute
        ↓
Lifecycle: CLAIM
        ↓
BEGIN_SANDBOX_PROVISIONING → SandboxPort (ManagedSandboxAdapter
                              → SandboxManager / DockerSandbox)
        ↓
SANDBOX_READY → Application StartRun (sandbox_id)
        ↓
START_ADAPTER → AdapterPort (SdkAdapterBridge → Adapter SDK)
        ↓
ADAPTER_STARTED → Adapter.run (ClaudeCodeAdapter streams NDM into
                  PipelineEventSink → EventPersistencePipeline)
        ↓
ADAPTER_FINISHED → Adapter.finish
        ↓
PERSIST_FINAL_EVENTS → pipeline.persist_final
        ↓
FINALS_PERSISTED → Application StartGrading
                 → GraderSdkScheduler (run_graders_isolated)
                 → Application RecordScore per ProducedScore
        ↓
GRADING_FINISHED → Application CompleteRun
        ↓
Worker ack
```

Composition: `agent_eval_workers.integration.build_production_harness`.

Boundaries held:

| Layer            | Unaware of                                     |
| ---------------- | ---------------------------------------------- |
| Execution Engine | Docker (SandboxPort only)                      |
| Worker chassis   | Claude / vendor APIs (Adapter factory at root) |
| Graders          | Each other + Application repositories          |
| Adapters         | Repositories / Application                     |
| Sandbox          | Domain / Application / Workers / Graders       |

Scores are recorded only through Application `RecordScore` while Domain
status is `Grading`. Judge LLM calls use injectable `JudgeProvider`
(`MockJudgeProvider` in tests).

## Mock orchestration (Phase 5)

Use `agent_eval_workers.execution_engine.build_orchestration_harness` for
deterministic verification without Docker, Claude CLI, or real Graders.

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
