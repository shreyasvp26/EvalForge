# ADR-0001: Foundational System Architecture

## Status

Accepted

## Date

2026-08-02

## Context

EvalForge exists to evaluate autonomous coding agents against standardized engineering tasks and produce objective, reproducible, comparable results. This is a different problem than scoring chat completions or running CI: an agent run is a multi-step, non-atomic process that produces tool calls, file edits, shell output, and a final diff, and the platform's job is to capture that process faithfully, grade it along multiple independent dimensions, and make the resulting data trustworthy enough to answer longitudinal questions — which agent regressed, which prompt revision helped, what a run cost — months or years after the run happened.

That last requirement is what makes this an architecture decision record rather than an implementation note. A platform whose core value is "compare this run to a run from six months ago and trust the comparison" cannot tolerate architectural drift, silent behavior changes, or ad hoc coupling between components that happen to be convenient to build together today. Every foundational decision below is chosen not for what it makes easy this quarter, but for what it keeps possible five years from now: adding new agents without destabilizing the execution engine, adding new graders without touching existing ones, and scaling any one plane without a coordinated rewrite of the others.

EvalForge is also, deliberately, infrastructure rather than an AI application. It does not generate content, does not make product decisions on a user's behalf, and its correctness is not measured by how well it converses — it is measured by whether the data it produces can be trusted. That framing pushes every decision toward boring, well-understood, operationally predictable technology over novel or clever approaches, because the platform's credibility depends on consistency, not sophistication.

This ADR is the first in the repository. It records the decisions that everything else — adapters, graders, the domain model's evolution — is built on top of. It assumes familiarity with the System Overview and Domain Model documents and does not restate them.

## Decision

### Backend owns the product

All product state and business logic live in the backend; the frontend is a renderer, not a source of truth. This is chosen because EvalForge must be usable from CI integrations, CLIs, and other automated callers as a first-class capability, not as an afterthought bolted onto a browser-first design. If business rules lived partly in the frontend, every non-browser client would either duplicate that logic or be a second-class citizen. Centralizing ownership in the backend guarantees a single, auditable place where every state mutation is validated, and it means the frontend can be redesigned or replaced without touching the rules that govern what a valid run, score, or suite looks like.

### API-first architecture

The frontend consumes the same API any external caller would use — there is no private internal API. This is a forcing function: it requires every feature to be designed as a stable, documented contract before it is designed as a UI. A platform whose UI and API drift apart quietly becomes un-integrable, and un-integrable is disqualifying for a tool whose primary consumers over time are other systems (CI pipelines, dashboards, future SDKs), not just people clicking through a browser.

### REST over GraphQL

EvalForge's domain is a small number of well-defined, resource-oriented entities — projects, suites, cases, runs, scores — accessed through predictable, largely enumerable patterns, not a deeply nested graph shaped by unpredictable client-driven queries. REST fits that shape directly: simpler per-endpoint authorization, simpler caching, and straightforward SDK generation. GraphQL's core advantage — letting heterogeneous clients each shape their own query against a complex graph — is a cost paid for a flexibility this platform does not need at V1. The tradeoff is real: REST can mean more round trips for deeply nested views (a run with its full event history and scores), and evolving REST payload shapes over time is more implementation-cost than GraphQL's client-driven field selection. That cost is acceptable because the API surface is stable and small enough that endpoint design can absorb it without turning into an under-fetching or over-fetching problem.

### Modular monolith for V1

The backend is deployed as a single service internally organized into clear module boundaries that mirror the system's planes, rather than as a set of independently deployed microservices. This is explicitly **not** a microservices architecture. At V1's scale, splitting the control plane into separately deployed services would add operational cost — network calls where function calls would do, distributed transaction concerns, independent deployment coordination — without a corresponding benefit, because there is no team-scaling or independent-release-cadence pressure yet that would justify paying for those boundaries at the infrastructure level. The module boundaries are drawn deliberately along the same seams a future service extraction would use, so that if a component's load profile or team ownership eventually demands independent deployment, it can be extracted without a redesign — the boundary already exists in code, extraction only changes where the process boundary sits.

### Asynchronous execution

Evaluation execution never happens inside an API request. Agent runs take minutes, involve untrusted code execution in a sandbox, and can fail in ways that have nothing to do with the API's health. Holding an HTTP connection open for that duration would couple API availability to execution duration and turn a slow or hung agent into an API-layer incident. Execution is instead handed off to a queue and performed by workers, with progress reported back asynchronously, so the API's responsiveness is never a function of how long an agent takes to finish a task.

### Adapter pattern

Every coding agent under evaluation has a different invocation surface, output format, and tool-calling convention, and that will remain true as new agents are added. The adapter is the only layer permitted to know those vendor-specific details; everything downstream — the execution engine, the event stream, every grader — operates only on the normalized domain model. This is what bounds the cost of supporting a new agent to writing one adapter, rather than threading agent-specific conditionals through every component that touches a run.

### Modular grader architecture

Objective correctness (did the tests pass) and subjective quality (is this a well-structured diff) are different problems with different failure modes, and a platform that conflates them into a single scoring path inherits the worst properties of both — a timeout in one grading concern blocking or corrupting an unrelated one. Keeping graders independently invokable and independently failing means a new grader can be added without modifying or destabilizing existing ones, and a single grader's bug is contained to that grader's scores.

### Immutable evaluation runs

A completed run is never mutated or deleted in place; events accumulate and status transitions forward, but historical data does not change retroactively. The platform's entire value proposition rests on trend and regression analysis being trustworthy — the moment a historical run can be silently edited, every comparison built on top of it becomes suspect, and there is no way to distinguish a real regression from a quietly altered baseline. Immutability is not a storage detail here; it is the property that makes the rest of the platform's analytical claims defensible.

### PostgreSQL as the system of record

Run lineage, scores, and state transitions are structured, relationally-integral data with real consistency requirements — a run cannot reference a suite version that does not exist, a score cannot outlive the grader run that produced it. That is exactly the problem a mature relational database is built to guarantee, and PostgreSQL specifically is chosen for its maturity, its support for the kind of partitioning strategy this platform will eventually need on high-write tables, and the operational familiarity that reduces risk in a system where data integrity is the product.

### Object storage for execution artifacts

Full event transcripts, diffs, and logs are large, write-once, and rarely queried relationally — they are fetched by reference, not joined against. Storing them inline in PostgreSQL would inflate the database with payloads that don't benefit from relational guarantees, slow down backups, and compete for I/O with the metadata queries that actually need to be fast. Object storage scales independently and cheaply for exactly this access pattern, while PostgreSQL stores only a pointer, keeping the system of record small and fast.

### Redis-backed asynchronous workers

The execution plane needs a task broker that is simple to operate, well understood, and fast enough that queue latency never becomes the perceived bottleneck in a workflow where actual execution takes minutes. Redis, paired with a mature task-worker framework, is chosen deliberately over a heavier message-bus solution because EvalForge's task volume is one task per run, not one task per fine-grained event — the workload does not need the durability and replay guarantees of a full event-streaming platform, and introducing one would be operational overhead without a matching benefit at this stage.

### Server-Sent Events for live progress

Run progress is reported to clients over Server-Sent Events rather than WebSockets. The traffic is inherently one-directional — the server pushes status and event updates; the client never needs to push data back over the same channel — and SSE is the simpler protocol for that shape: it rides over plain HTTP, works through standard infrastructure without special proxy handling, and reconnects with less custom logic than a WebSocket client typically needs. The tradeoff is that SSE cannot support bidirectional use cases if one ever emerges (for example, a client sending commands back over the same live channel); if that need arises, it would be added as a separate, explicit channel rather than by retrofitting bidirectionality onto the progress stream. For a platform where the entire live-update surface is "tell me what's happening to this run," that tradeoff favors SSE cleanly.

## Consequences

### Positive

Every plane can evolve independently as long as it respects its existing boundary, which lets execution scale, grading logic change, and the frontend be rebuilt without coordinated releases across the system. Immutable runs and pervasive versioning make the platform's comparisons defensible by construction rather than by discipline. The adapter and grader patterns bound the cost of the two things most likely to grow over time — supported agents and grading criteria — to additive work rather than invasive change.

### Negative

A modular monolith means the backend deploys as one unit; a bug or resource spike in one module can, in principle, affect the availability of unrelated modules until the boundaries are extracted into separate services. REST's simplicity comes at the cost of some over-fetching for deeply nested views like a full run history. SSE's one-directional nature means any future bidirectional live interaction requires a new channel rather than extending the existing one.

### Risks

The biggest risk is boundary erosion: without deliberate discipline, a modular monolith's internal module boundaries can decay into implicit coupling that makes eventual service extraction far harder than it needs to be. A second risk is that immutability and versioning, while architecturally sound, add real friction to any workflow that "just" wants to fix a small mistake in historical data — the correct fix is always a new version, never an edit, and that discipline has to be enforced consistently or the platform's core guarantee quietly erodes.

### Mitigations

Module boundaries are drawn along the same seams that a future service extraction would use, and treated as architecture-review-worthy if crossed casually — this keeps the monolith's internal structure honest without paying for premature service extraction. Immutability is enforced at the data-model level, not left to application-code discipline alone, so "just this once" edits are structurally difficult rather than merely discouraged.

## Alternatives Considered

**Microservices.** Rejected for V1 because there is no team-scaling or independent-deployment pressure that justifies the operational cost of distributed transactions, network-call overhead where function calls would do, and independent release coordination. The modular monolith preserves the option to extract services later along boundaries already established in code.

**GraphQL.** Rejected because EvalForge's domain is a small set of resource-oriented entities with predictable access patterns, not a graph shaped by heterogeneous client query needs. The operational simplicity REST offers — caching, per-endpoint auth, SDK generation — outweighs GraphQL's flexibility for this domain.

**Synchronous execution.** Rejected because agent runs take minutes and involve untrusted, potentially long-hanging or failing sandboxed execution. Coupling API request/response cycles to that duration would make API availability hostage to execution health, which is architecturally unacceptable for a control plane other systems depend on.

**Storing artifacts in PostgreSQL.** Rejected because large, write-once transcripts and diffs do not benefit from relational guarantees and would inflate the database, slow backups, and compete for I/O with the metadata queries that need to stay fast. Object storage scales for exactly this access pattern; Postgres stores a pointer.

**Tight coupling between agents and the execution engine.** Rejected because it would mean every new agent requires changes to shared execution and grading code, rather than the addition of a single isolated adapter. This is precisely the coupling the adapter pattern exists to prevent.

**Mutable evaluation history.** Rejected because the platform's core value — trustworthy longitudinal and regression comparison — depends entirely on historical runs being incapable of silent change. Any workflow that appears to need "editing" a past run is better served by creating a new, correctly versioned run.

## Future Evolution

None of the decisions above are treated as permanent constraints on the system's shape — they are the right starting point, chosen deliberately to be extended rather than replaced. Likely future evolutions include: extracting one or more modules of the monolith into independently deployed services once team or load pressures justify the operational cost, the boundaries for which already exist in the current module structure; running multiple specialized worker pools (for example, segmented by sandbox resource class) rather than a single undifferentiated pool; introducing an event bus if the platform's internal communication needs outgrow what a task queue and REST boundaries can cleanly express; adding multi-tenancy on top of the existing project-scoped authorization model, which was chosen specifically so that an organization layer above it is additive rather than a redesign; and exposing public-facing APIs or a leaderboard as a new read path over the same immutable run and score data already being persisted.

These are extensions this ADR anticipates, not requirements it is trying to satisfy prematurely. The architecture's success criterion is that when each of these becomes necessary, it is implemented by adding a component or a boundary, not by rewriting one.

## References

- System Overview (`docs/architecture/system-overview.md`)
- Domain Model (`docs/architecture/domain-model.md`)