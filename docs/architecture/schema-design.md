# Schema Design

## Purpose

Database Design establishes the principles governing EvalForge's relational storage: PostgreSQL as system of record, metadata-versus-artifact separation, immutability, explicit versioning, aggregate-aligned ownership. It deliberately stopped short of naming every table, because a principle and its concrete realization are different kinds of decision, made at different times, and conflating them would have made Database Design harder to keep stable — a document that names every table changes every time a new entity is added, while a document that only states principles should almost never need to change once those principles are right.

This document is where that stops being true. Schema Design is the exhaustive, entity-by-entity specification of every logical table in EvalForge's relational schema: what it is, what identifies it, what it relates to, who owns it, how it lives and dies, and what must always be true about it. It is written so that a backend engineer can go from this document directly to a SQLAlchemy model without making a single undocumented modeling decision along the way. Where Database Design answered "what principles govern our storage," this document answers "given those principles, what exactly exists."

This is still a logical specification, not a physical one. Nothing here names a PostgreSQL column type, an index, a constraint syntax, or a migration step — those are implementation choices made against this document, informed by it, but not part of it. The distinction matters for the same reason Database Design gave for separating itself from the Domain Model: a document that mixes logical structure with physical implementation choices loses the ability to have the latter change (a column type widened, an index added, a constraint's enforcement mechanism revised) without touching the former. This document should be stable in exactly the way a well-designed schema's logical shape is stable — evolving only when the business or domain genuinely changes, not when an implementation detail beneath it does.

## Schema Philosophy

**Logical schema versus physical storage.** Every entity described below is a logical table: a named collection of logically related fields with a defined identity, defined relationships to other logical tables, and defined lifecycle rules. How that logical table is physically realized — partitioned, indexed, denormalized for a specific read path — is a Database Design and implementation concern, already addressed in principle and left to later documents in specifics. This document's tables are the contract those physical decisions must honor, not a preview of them.

**Relational modeling, not document modeling.** Every relationship in this schema is expressed through explicit foreign-key references between narrow, single-purpose tables, never through an embedded document, a JSON blob standing in for a relationship the database could otherwise enforce, or an array-valued column doing the work an association table should do. This is a direct continuation of Database Design's stance that explicit foreign keys are worth their write-time cost, applied now at the level of naming exactly which tables exist and which columns on them are foreign keys.

**Immutable rows as the default, not the exception.** The majority of the tables in this schema — every version table, every execution-time table — are insert-only: a row, once written, is never the target of an update in the platform's normal operation. This document calls out explicitly, table by table, which rows are immutable once written and which few are legitimately mutable (chiefly, a Run's status field advancing through its lifecycle, and a small number of administrative fields on definitional entities like a Project's settings). Immutability is treated as something each table must earn an exception from, not something each table must opt into.

**Normalized source of truth.** Every fact in this schema is stored in exactly one table, owned by exactly one entity, and referenced by foreign key everywhere else it is needed. No table in this document duplicates a fact that another table already owns — where a Run needs to know which Case it was executed against, it stores a foreign key to a Case Version, never a copy of that Case Version's content. This is what keeps the schema trustworthy as the single source of truth Database Design established it must be; any future denormalized read model, per that document's Normalization Philosophy, is built from this schema, never a substitute for it.

**Explicit ownership over implicit convention.** Every table below states, unambiguously, which other table (if any) owns its lifecycle. A table that is "owned" by another cannot exist without a valid reference to its owner and is deleted only as a consequence of its owner's own deliberate removal (per Database Design's deletion philosophy). A table that merely "references" another is never implied to be owned by what it references, no matter how central that reference is to the table's meaning. This distinction, carried over directly from Database Design's Aggregate-to-Database Mapping, is restated for every single table in this document precisely because it is the distinction most likely to be gotten wrong by an engineer working from an incomplete mental model rather than this specification.

**Version-first modeling.** Every entity the Domain Model treats as versioned is modeled here as two tables from the outset — a stable-identity table and an immutable-version table — never as a single mutable table with a "current version" notion bolted on later. This is not a modeling style chosen for this document; it is a direct structural consequence of Database Design's Versioning Model, and every version table below follows the identical shape for exactly that reason: consistency across all six versioned axes is itself a correctness property, since an engineer who understands how Case Versions work should never need to relearn the pattern to understand Grader Versions.

## Entity Inventory

The complete set of logical tables in EvalForge's schema falls into six groups, mirroring the bounded contexts already established in the Domain Model and Backend Architecture.

**Evaluation Management.** Project, Suite, Suite Version, Case, Case Version, Prompt, Prompt Version.

**Agent Integration.** Agent, Agent Version, Adapter, Adapter Version.

**Grading.** Grader, Grader Version.

**Execution.** Run, Execution Event, Artifact, Score.

**Association and Composition.** Suite Composition, Case Grader Declaration.

**Platform Integrity.** Audit Log.

Two concepts from the Domain Model are deliberately *not* modeled as their own tables, and this is stated explicitly here because their absence could otherwise be read as an oversight rather than a decision. The **Execution Engine** is, per the Domain Model, "a standing capability of the platform" rather than an instance-lifecycled entity — it has no identity, no created-at timestamp, and nothing about it needs to be queried relationally, so it has no table. The **Sandbox** is provisioned fresh per Run and torn down at the Run's conclusion, retaining no state between Runs and, critically, producing no fact of its own that is not already captured as an Execution Event or Artifact once translated across its boundary — a Sandbox's existence during a Run is fully represented by the Run's own lifecycle timestamps and the events it produced, so a dedicated Sandbox table would store nothing the rest of the schema does not already capture, and is deliberately omitted to avoid exactly that kind of redundant, driftable duplication. Version lineage, similarly, is not modeled as a standalone table — it is a self-referencing predecessor field on each version table, discussed in Version Tables below, rather than a separate entity, because lineage is a property of a version, not a thing that exists independently of one.

## Table Specifications

### Project

**Purpose.** The top-level authorization and organizational scoping boundary for all evaluation activity.

**Responsibility.** Owns every Suite and every Case created within it; is the boundary every access-control decision is ultimately scoped against.

**Primary Identity.** A single stable identifier. A Project has no version concept of its own — its settings may change in place over its lifetime, unlike every other table in the Evaluation Management group.

**Relationships.** Referenced by every Suite and every Case belonging to it. Has no upward reference — Project is the root of the ownership graph.

**Ownership.** Owns Suites and Cases directly. Owns nothing further transitively in the relational sense; a Project does not cascade-own Runs, since Runs are owned by the Cases and Suites they reference only through pinned version references, not through direct Project ownership (see Relationship Model).

**Lifecycle.** Long-lived, created once, essentially never deleted in normal operation; may be deactivated administratively without removing the historical Suites, Cases, and Runs that reference it.

**Important Constraints.** A Suite or Case cannot exist without a valid Project reference. A Project's identifier, once assigned, never changes, since every downstream table's authorization scoping depends on it remaining stable.

**Expected Cardinality.** Low — a platform-operating organization is expected to have relatively few Projects (tens to low hundreds), each accumulating a large volume of Suites, Cases, and Runs beneath it.

**Access Patterns.** Looked up by identifier on nearly every authorization check in the system; rarely scanned or listed in bulk.

### Suite

**Purpose.** The stable identity of a named, evaluable collection of Cases — "the Python Refactoring Suite" as a persistent concept independent of any particular composition of it.

**Responsibility.** Anchors the identity that Suite Versions are versions *of*; holds whatever administrative metadata (name, description, active/deprecated status) is meaningful at the stable-identity level rather than per version.

**Primary Identity.** A single stable identifier, distinct from any Suite Version's identifier.

**Relationships.** Belongs to exactly one Project. Has many Suite Versions.

**Ownership.** Owned by its Project. Owns its Suite Versions.

**Lifecycle.** Created once per named suite concept; its administrative status (active, deprecated) may change, but this table itself never accumulates the kind of history that requires versioning — that history lives in Suite Version.

**Important Constraints.** Cannot exist without a valid Project reference. A Suite's name is expected to be unique within its Project, since two identically named suites within the same scope would be indistinguishable to the people selecting between them.

**Expected Cardinality.** Moderate — tens to low hundreds of Suites per Project, each with a growing history of Suite Versions beneath it.

**Access Patterns.** Browsed and searched by name within a Project; resolved to its latest or a specific Suite Version when a user is selecting what to run.

### Suite Version

**Purpose.** An immutable, point-in-time composition of Cases that constitutes one comparable evaluation workload.

**Responsibility.** Records exactly which Case Versions, in what order, make up this specific version of the Suite. Is the entity a Run actually pins when executed as part of a suite.

**Primary Identity.** A version identifier, unique within its Suite, paired with a reference back to the stable Suite it versions.

**Relationships.** Belongs to exactly one Suite. Composes many Case Versions through the Suite Composition association table (see Association Tables). References the Suite Version it supersedes, if any (its lineage predecessor).

**Ownership.** Owned by its Suite. Owns the Suite Composition rows that record its specific Case Version composition — those association rows have no meaning independent of the Suite Version they belong to.

**Lifecycle.** Written once, at creation, and never modified thereafter. A change to a Suite's composition produces an entirely new Suite Version row rather than altering an existing one, per Database Design's Versioning Model.

**Important Constraints.** Immutable after creation — no field on this table is a legitimate target of an update once written, including its composition, which is why composition is captured via association rows written atomically alongside the Suite Version rather than being editable afterward. Must reference a valid Suite. Its lineage predecessor, when present, must belong to the same Suite.

**Expected Cardinality.** A Suite is expected to accumulate a modest but ongoing number of versions over its lifetime — low tens per Suite is typical, growing slowly as composition is deliberately curated rather than churned frequently.

**Access Patterns.** Fetched by identifier when a Run pins it; its composition is read in full when a Suite is executed or displayed; its lineage is traversed when comparing a Suite's evolution over time.

### Case

**Purpose.** The stable identity of a single engineering task — a bug fix, feature request, refactor, or security patch — independent of any particular revision of its content.

**Responsibility.** Anchors the identity that Case Versions are versions of, analogous to Suite's relationship to Suite Version.

**Primary Identity.** A single stable identifier, distinct from any Case Version's identifier.

**Relationships.** Belongs to exactly one Project. Has many Case Versions. Referenced by zero or more Suite Versions (through Suite Composition), never owned by any of them.

**Ownership.** Owned by its Project. Owns its Case Versions.

**Lifecycle.** Created once per task concept; administrative status may change (active, deprecated), but content revisions live entirely in Case Version.

**Important Constraints.** Cannot exist without a valid Project reference.

**Expected Cardinality.** The largest definitional-entity population in the schema by count — a Project may accumulate hundreds to thousands of Cases over time, each with its own version history.

**Access Patterns.** Browsed and searched within a Project by name, tags, or task category (where such metadata exists at the Case level rather than per version); resolved to a specific Case Version when composed into a Suite or executed directly.

### Case Version

**Purpose.** An immutable, point-in-time definition of a task's content: its description, its reference repository state, and its expected checks.

**Responsibility.** Is the entity a Run actually pins when evaluated against this Case; is the entity that declares which Graders are applicable, via Case Grader Declaration.

**Primary Identity.** A version identifier, unique within its Case, paired with a reference back to the stable Case it versions.

**Relationships.** Belongs to exactly one Case. Defines exactly one Prompt (whose own content is separately versioned as Prompt Version). Declares applicable Graders through Case Grader Declaration. Referenced by Run when a Run is executed against this Case Version, and by Suite Composition when included in a Suite Version.

**Ownership.** Owned by its Case.

**Lifecycle.** Written once and never modified. A content edit — a changed description, a changed reference repository state, a changed set of expected checks — produces a new Case Version row, never an update to an existing one.

**Important Constraints.** Immutable after creation. Must reference a valid Case. Its lineage predecessor, when present, must belong to the same Case. A Case Version that has ever been referenced by a Run (directly, or transitively through a Suite Version a Run pinned) can never be removed, regardless of the Case's own administrative status, per Database Design's referential-integrity philosophy.

**Expected Cardinality.** A Case is expected to accumulate a small number of versions relative to its lifetime — task definitions are refined occasionally, not continuously — typically single digits to low tens per Case.

**Access Patterns.** Fetched by identifier both when a Run is created (to pin it) and when a Run's historical record is displayed or debugged; its declared Graders are read whenever a Run against it needs to determine which Graders to invoke.

### Prompt

**Purpose.** The stable identity of the instruction content handed to an agent for a Case, versioned independently of the Case's own content because prompt wording is iterated on its own cadence.

**Responsibility.** Anchors the identity that Prompt Versions are versions of.

**Primary Identity.** A single stable identifier, distinct from any Prompt Version's identifier.

**Relationships.** Belongs to exactly one Case (created alongside it, per the Domain Model). Has many Prompt Versions.

**Ownership.** Owned by its Case. Owns its Prompt Versions.

**Lifecycle.** Created once, alongside its Case; its own row is essentially administrative, with all real content history living in Prompt Version.

**Important Constraints.** Cannot exist without a valid Case reference.

**Expected Cardinality.** Exactly one Prompt per Case in the common case, since a Case defines exactly one Prompt per the Domain Model, though the underlying content is free to accumulate many Prompt Versions.

**Access Patterns.** Resolved through its owning Case when a Case Version is fetched; rarely queried independently of that context.

### Prompt Version

**Purpose.** An immutable, point-in-time revision of the actual instruction text given to an agent.

**Responsibility.** Is the entity a Run pins independently of the Case Version it was paired with, which is precisely what makes prompt-regression analysis possible while holding the Case constant, per the Domain Model.

**Primary Identity.** A version identifier, unique within its Prompt, paired with a reference back to the stable Prompt it versions.

**Relationships.** Belongs to exactly one Prompt. Referenced by Run when a Run pins this specific Prompt Version.

**Ownership.** Owned by its Prompt.

**Lifecycle.** Written once and never modified; a wording change produces a new Prompt Version row.

**Important Constraints.** Immutable after creation. Must reference a valid Prompt. Its lineage predecessor, when present, must belong to the same Prompt. Once referenced by any Run, permanently retained regardless of the Prompt's own administrative status.

**Expected Cardinality.** Typically the most frequently revised version table relative to its parent — prompt wording is iterated more often than the underlying Case content itself, so a Case's Prompt may accumulate substantially more versions than the Case accumulates Case Versions.

**Access Patterns.** Fetched by identifier when a Run is created and pinned; read when reconstructing exactly what instruction content an Agent received for a specific historical Run.

### Agent

**Purpose.** The stable identity of a coding agent product under evaluation — the subject under test, independent of any specific release.

**Responsibility.** Anchors the identity that Agent Versions are versions of; is the entity connected to exactly one Adapter.

**Primary Identity.** A single stable identifier.

**Relationships.** Has many Agent Versions. Connected to exactly one Adapter (which itself carries its own, independently versioned history).

**Ownership.** Owns its Agent Versions. Owns nothing else — an Agent does not own the Adapter connected to it, since Adapter and Agent are independently versioned per the Domain Model's explicit statement that one can change while the other does not.

**Lifecycle.** Long-lived, created once when a coding agent product is first onboarded for evaluation, and expected to persist for as long as the vendor's product exists and EvalForge continues to support it.

**Important Constraints.** An Agent's connected Adapter reference must always resolve to a valid Adapter; an Agent without any usable Adapter cannot be the target of a new Run, though this is an application-layer validation rather than a structural impossibility, since an Agent may legitimately be onboarded before its Adapter implementation is complete.

**Expected Cardinality.** Low — the number of distinct coding agent products under evaluation is expected to remain in the single digits to low tens even at platform maturity, growing slowly as new agents enter the market.

**Access Patterns.** Selected by identifier when a Run is created; resolved alongside its Agent Versions when populating a comparison dashboard across agents.

### Agent Version

**Purpose.** An immutable record of a specific release or build of an Agent that the platform has chosen to track.

**Responsibility.** Is the entity a Run pins, since agent behavior is understood to shift across vendor releases independent of anything EvalForge controls, per the Domain Model.

**Primary Identity.** A version identifier, unique within its Agent, paired with a reference back to the stable Agent it versions.

**Relationships.** Belongs to exactly one Agent. Referenced by Run when a Run pins this specific Agent Version.

**Ownership.** Owned by its Agent.

**Lifecycle.** Written once, when the platform begins tracking a new release or build of the underlying Agent, and never modified thereafter.

**Important Constraints.** Immutable after creation. Must reference a valid Agent. Once referenced by any Run, permanently retained.

**Expected Cardinality.** Grows steadily but modestly over an Agent's lifetime, tracking the pace of the vendor's own release cadence — typically tens to low hundreds of versions accumulated over a platform's multi-year lifetime per actively tracked Agent.

**Access Patterns.** Fetched by identifier when a Run is created; central to any query comparing behavior or scores across different releases of the same Agent.

### Adapter

**Purpose.** The stable identity of the vendor-specific translation layer between one Agent's native interface and EvalForge's Normalized Domain Model.

**Responsibility.** Anchors the identity that Adapter Versions are versions of; is the only concept, per the Backend Architecture, permitted to know anything agent-specific — a responsibility this table records the identity of but does not itself implement.

**Primary Identity.** A single stable identifier.

**Relationships.** Connected to exactly one Agent. Has many Adapter Versions.

**Ownership.** Owns its Adapter Versions. Not owned by the Agent it is connected to — the connection is a reference, not ownership, precisely because Adapter and Agent evolve on independent axes and neither's lifecycle should be bound to the other's.

**Lifecycle.** Created when an Agent is first onboarded; persists for as long as that Agent remains supported, though its specific Adapter Versions come and go independently of the Agent's own version history.

**Important Constraints.** Must reference a valid Agent.

**Expected Cardinality.** One Adapter per supported Agent in the common case, matching the one-to-one connection the Domain Model describes.

**Access Patterns.** Resolved through its connected Agent when the Execution Engine needs to determine which Adapter to invoke for a Run.

### Adapter Version

**Purpose.** An immutable record of a specific revision of the mapping logic between an Agent's native output and the Normalized Domain Model.

**Responsibility.** Is the entity a Run pins, distinct from the Agent Version it is paired with, so that adapter-caused behavior changes can be distinguished from agent-caused ones, per the Domain Model.

**Primary Identity.** A version identifier, unique within its Adapter, paired with a reference back to the stable Adapter it versions.

**Relationships.** Belongs to exactly one Adapter. Referenced by Run when a Run pins this specific Adapter Version.

**Ownership.** Owned by its Adapter.

**Lifecycle.** Written once, when the mapping logic is revised (independent of whether the underlying Agent has changed), and never modified thereafter.

**Important Constraints.** Immutable after creation. Must reference a valid Adapter. Once referenced by any Run, permanently retained.

**Expected Cardinality.** Revised less frequently than Agent Version in the typical case, since adapter mapping logic is expected to be more stable than the pace of vendor releases, though a vendor's output-format change can force an Adapter Version revision independent of any Agent Version change.

**Access Patterns.** Fetched by identifier when a Run is created; read when distinguishing whether an observed behavior change traces to the Agent or to the translation layer.

### Grader

**Purpose.** The stable identity of an independently invokable grading capability — objective or rubric-based — that produces Scores for completed Runs.

**Responsibility.** Anchors the identity that Grader Versions are versions of; is the entity Case Versions declare as applicable via Case Grader Declaration.

**Primary Identity.** A single stable identifier.

**Relationships.** Has many Grader Versions. Declared applicable by zero or more Case Versions through Case Grader Declaration.

**Ownership.** Owns its Grader Versions. Owns nothing else — a Grader does not own the Scores it eventually produces, since Scores belong to the Run aggregate, per Database Design.

**Lifecycle.** Created once when a grading capability is authored; persists as long as that grading capability remains supported by the platform.

**Important Constraints.** None beyond basic identity uniqueness — a Grader with no Grader Versions yet is a legitimate, if not yet usable, state during authoring.

**Expected Cardinality.** Low to moderate — expected to grow steadily as new grading capabilities are authored, but nowhere near the volume of Cases or Runs; low tens to low hundreds across the platform's lifetime.

**Access Patterns.** Selected when declaring which Graders apply to a Case Version; resolved alongside its Grader Versions when populating a grader-performance or grader-reliability view.

### Grader Version

**Purpose.** An immutable record of a specific revision of a Grader's rubric wording, scoring thresholds, or objective-check logic.

**Responsibility.** Is the entity a Score is produced by and permanently attributed to, which is what makes it possible to tell whether an apparent score regression reflects a real change in agent behavior or simply a change in how the grader scores, per the Domain Model.

**Primary Identity.** A version identifier, unique within its Grader, paired with a reference back to the stable Grader it versions.

**Relationships.** Belongs to exactly one Grader. Referenced by Score, exactly once per Score, when that Grader Version produces a graded outcome for a Run.

**Ownership.** Owned by its Grader.

**Lifecycle.** Written once, when the grader's rubric or logic is revised, and never modified thereafter.

**Important Constraints.** Immutable after creation. Must reference a valid Grader. Once referenced by any Score, permanently retained.

**Expected Cardinality.** Varies substantially by Grader — an objective Grader's logic may be revised rarely, while a rubric-based Grader's wording may be tuned more frequently in response to observed scoring behavior.

**Access Patterns.** Referenced from every Score row; read when explaining a scoring change or when a Grader SDK-based registration (see Future Extensions) needs to resolve the exact version active at a point in time.

### Run

**Purpose.** A single, immutable execution of one Agent Version against one Case Version, and the central entity around which nearly every other execution-time table is organized.

**Responsibility.** Records the full set of pinned versions that fully specify what was evaluated and how, per the Domain Model's versioning philosophy; owns its Execution Events, Artifacts, and Scores completely; carries its own lifecycle status and execution-cost facts.

**Primary Identity.** A single stable identifier, generated at creation and never reused. A Run has no version concept of its own — it is not a versioned entity in the Domain Model's sense, it *is* the entity that pins versions of everything else.

**Relationships.** References exactly one Case Version, one Prompt Version, one Agent Version, one Adapter Version, and — when executed as part of a suite — one Suite Version. Owns many Execution Events, many Artifacts, and one Score per applicable Grader Version. Referenced by every Execution Event, Artifact, and Score that belongs to it.

**Ownership.** Not owned by any other table — a Run's creation is triggered by a Project member's action, but a Run is not owned by the Case Version, Agent Version, or any other entity it references, since those entities have independent lifecycles and a Run's existence never controls theirs. Owns its Execution Events, Artifacts, and Scores completely.

**Lifecycle.** Created once, with all pinned version references fixed permanently at that moment (the Run Created domain event). Its status field is the one legitimate exception to this table's otherwise-immutable posture: status advances forward through the finite state machine the Domain Model defines (queued, running, grading, and a terminal state), and this forward-only status transition is the single mutable aspect of an otherwise append-only entity. Once terminal, permanently closed to any further change, including to status.

**Important Constraints.** Every one of its five pinned version references must resolve to a valid, existing version row at creation time, and none of those references may ever be altered afterward. Status transitions must follow the Domain Model's defined state machine — a transition to an invalid next state is a constraint violation, not a legitimate operation. A Run cannot be deleted in normal operation, only through the deliberate retention process Database Design describes.

**Expected Cardinality.** The largest table in the schema by row count over the platform's lifetime — millions of rows expected, growing continuously with every evaluation triggered.

**Access Patterns.** Created and read by identifier constantly; queried in bulk, filtered by Case, Suite, Agent, and time range, for the dashboard and trend-analysis workloads Database Design's Indexing Philosophy discusses; status is polled or streamed while a Run is active.

### Execution Event

**Purpose.** A discrete, timestamped record of something that happened during a Run's execution — a tool call, a file edit, a shell command, or a piece of output.

**Responsibility.** The ordered sequence of Execution Events for a Run *is* that Run's execution history, per the Domain Model — the record that answers "why did this evaluation fail" without needing to reproduce a possibly non-deterministic agent behavior.

**Primary Identity.** A single stable identifier, combined with an explicit sequence position that is unique within its owning Run and establishes the strict ordering the Domain Model requires, independent of insertion timing under concurrent writers (per Database Design's Concurrency section).

**Relationships.** Belongs to exactly one Run. May reference one or more Artifacts, for events whose full payload is too large to carry inline.

**Ownership.** Owned by its Run.

**Lifecycle.** Written once, in strict sequence, during an active Run's execution, and never altered or removed afterward — the archetypal append-only table in this schema.

**Important Constraints.** Must reference a valid, currently active Run — an Execution Event cannot be recorded against a Run that has already reached a terminal state, since a terminal Run's history is permanently closed. Sequence position must be unique within its Run. No update operation against this table's existing rows is a legitimate application behavior under any circumstance.

**Expected Cardinality.** The highest-volume table in the entire schema — hundreds of millions of rows expected over the platform's lifetime, growing continuously and rapidly during every active Run.

**Access Patterns.** Written at high frequency during execution; read in full sequence for a single Run when displaying or debugging that Run's history; read by Graders during the grading phase; essentially never queried across Runs in bulk except through the time-partitioned, aggregate-oriented paths Database Design's Partitioning Strategy describes.

### Artifact

**Purpose.** A large, immutable payload associated with a Run — a diff, a log, a full transcript — that is content rather than metadata.

**Responsibility.** Holds the reference (per Database Design's Storage Strategy) to the actual payload's location in object storage, along with the minimal relationally-useful facts about it (its size, its content classification, its integrity checksum), without holding the payload's content itself.

**Primary Identity.** A single stable identifier.

**Relationships.** Belongs to exactly one Run. May be referenced by one or more Execution Events, for events whose payload this Artifact represents.

**Ownership.** Owned by its Run. May also be created by the grading process, per the Domain Model, when a Grader itself produces a durable output — in that case it is still owned by the Run being graded, not by the Grader that produced it, consistent with Score's identical ownership pattern.

**Lifecycle.** Written once, when the underlying payload is durably persisted to object storage, and never modified afterward — its reference, once written, never points somewhere else, even if the underlying object storage location is later migrated to a different storage tier (a physical, not logical, change, per Database Design's Retention Strategy).

**Important Constraints.** Must reference a valid Run. Its object storage reference must be resolvable at write time; a row referencing content that was never successfully persisted represents exactly the "partial-artifact state" the System Overview's Failure Model calls for handling explicitly, not silently.

**Expected Cardinality.** Substantial but a small fraction of Execution Event volume — most events do not produce an oversized payload requiring separate artifact storage — tens of millions of rows expected over the platform's lifetime.

**Access Patterns.** Written during and immediately after a Run's execution; fetched by reference (never joined against for its content) when a human or Grader needs the actual payload; its metadata (size, checksum) is occasionally queried in aggregate for storage-planning purposes.

### Score

**Purpose.** A single graded output value, objective or rubric-based, attached to a Run and produced by exactly one Grader at exactly one Grader Version.

**Responsibility.** Is the domain's answer to "how did this Run do," decomposed into as many independent measurements as there are applicable Graders, per the Domain Model.

**Primary Identity.** A single stable identifier.

**Relationships.** Belongs to exactly one Run. References exactly one Grader Version.

**Ownership.** Owned by its Run, not by the Grader Version that produced it — a Grader Version can be referenced by many Scores across many different Runs, and none of those Score rows are owned by the Grader in the aggregate sense, per Database Design.

**Lifecycle.** Written once, atomically, when its producing Grader completes during a Run's grading phase, and immutable thereafter.

**Important Constraints.** Must reference both a valid Run and a valid Grader Version. A Run may have at most one Score per Grader Version — this uniqueness constraint is what makes the idempotent-insert behavior Database Design's Concurrency section describes possible: a redelivered grading task's insert either matches an already-persisted Score for the same Run-and-Grader-Version pair (a no-op) or is rejected, never silently duplicated. Can only be created while its owning Run is in the Grading state or has reached a terminal state carrying partial-grading metadata; never created against a Run that has not yet begun grading.

**Expected Cardinality.** A modest multiple of Run volume — typically single digits of Scores per Run, one per applicable Grader — tens of millions of rows expected over the platform's lifetime.

**Access Patterns.** Fetched in full for a single Run when displaying its results; aggregated and compared across many Runs, filtered by Grader and time range, for the regression-detection and trend-analysis workloads that are the platform's primary analytical purpose.

### Suite Composition

**Purpose.** The association entity recording which Case Versions, in what order, belong to a specific Suite Version.

**Responsibility.** Exists because a Suite Version's composition is itself meaningful, ordered data — not merely a set membership fact — and because the same Case Version can belong to many different Suite Versions across many different Suites, which a plain foreign key on either side could not express.

**Primary Identity.** A composite identity formed by the Suite Version and the Case Version it associates, together with an explicit ordering position that records where this Case Version sits within the Suite Version's sequence.

**Relationships.** Belongs to exactly one Suite Version. References exactly one Case Version.

**Ownership.** Owned by its Suite Version — a Suite Composition row has no independent meaning or lifecycle outside the specific Suite Version it belongs to, and is written atomically alongside that Suite Version's creation, never afterward.

**Lifecycle.** Written once, at the moment its owning Suite Version is created, and never modified thereafter — consistent with the Suite Version's own immutability, since an editable composition would defeat the purpose of versioning the Suite in the first place.

**Important Constraints.** Must reference a valid Suite Version and a valid Case Version. The Case Version referenced must belong to the same Project as the Suite Version's own Suite, since Suite and Case are both Project-scoped and composing across Project boundaries would violate the authorization scoping Project exists to enforce. Ordering position must be unique within its Suite Version.

**Expected Cardinality.** A multiple of Suite Version volume proportional to typical suite size — a Suite Version composing dozens of Cases produces dozens of Suite Composition rows.

**Access Patterns.** Read in full, in order, whenever a Suite Version is executed or displayed; essentially never queried independently of its owning Suite Version.

### Case Grader Declaration

**Purpose.** The association entity recording which Graders are declared applicable to a given Case Version.

**Responsibility.** Exists because Case-to-Grader is a genuine many-to-many relationship — a single Grader (a generic test-pass/fail check, for instance) is typically applicable to many different Cases, and a single Case typically declares several applicable Graders — and because this declaration itself, independent of any specific Run, is a fact worth storing explicitly rather than inferring.

**Primary Identity.** A composite identity formed by the Case Version and the Grader it declares applicable.

**Relationships.** Belongs to exactly one Case Version. References exactly one Grader — the stable Grader identity, not a specific Grader Version, since which Grader Version is actually invoked is resolved at Run time and recorded on the resulting Score, not fixed in advance by the declaration.

**Ownership.** Owned by its Case Version — a declaration has no meaning independent of the specific Case Version it applies to, and a new Case Version that wishes to declare the same Graders applicable does so with its own new Case Grader Declaration rows, never by reusing the prior Case Version's.

**Lifecycle.** Written once, alongside its Case Version's creation (or shortly after, during authoring, before the Case Version is published for use), and not modified thereafter — a change to which Graders apply to a Case is itself a content change that belongs on a new Case Version, consistent with Case Version's own immutability.

**Important Constraints.** Must reference a valid Case Version and a valid Grader. A given Grader should not be declared applicable to the same Case Version more than once, since a duplicate declaration would carry no additional meaning and would only create ambiguity about how many times that Grader should run against Runs of this Case Version.

**Expected Cardinality.** A small multiple of Case Version volume — typically a handful of declared Graders per Case Version.

**Access Patterns.** Read whenever a Run against a given Case Version needs to determine which Graders to invoke during its grading phase; rarely queried from the Grader side, though a "which Cases use this Grader" view would read this table filtered by Grader.

### Audit Log

**Purpose.** The record of administrative and definitional actions — who created a Suite, who triggered a Run, who modified a Case — distinct from the execution-time facts captured in Execution Event.

**Responsibility.** Provides the accountability trail the System Overview's Observability section requires, retained independently of the run-data lifecycle policies that might eventually govern other tables, per Database Design's Auditability section.

**Primary Identity.** A single stable identifier.

**Relationships.** References the actor who performed the recorded action, the Project the action was scoped to (where applicable), and, loosely, whatever entity was the subject of the action (a created Suite, a triggered Run) — this last reference is intentionally more permissive than the tightly-typed foreign keys elsewhere in this schema, since an Audit Log entry must remain valid and readable even if, in some future retention scenario, the specific entity it describes has since been archived out of the primary schema's active tables.

**Ownership.** Not owned by any other table in the aggregate sense — an Audit Log entry is a standalone fact about an action taken, not a component of the entity it describes.

**Lifecycle.** Written once, at the moment the administrative action occurs, and never modified thereafter.

**Important Constraints.** Must reference a valid actor and, where applicable, a valid Project. Never a target of an update or, in normal operation, a delete — an audit trail that can be edited after the fact defeats its own purpose.

**Expected Cardinality.** Moderate — proportional to administrative and run-triggering activity rather than to execution volume itself; substantially smaller than Execution Event, though still a continuously growing table over the platform's lifetime.

**Access Patterns.** Queried by actor, by Project, or by time range when investigating who did what and when; essentially never read as part of the platform's ordinary evaluation-serving workloads, and is not part of the execution flow in any way, per the Backend Architecture.

## Relationship Model

The tables above realize four distinct relationship shapes, each used deliberately rather than defaulted into.

**One-to-many** is the most common shape and represents true ownership in every instance: Project to Suite and Case, Suite to Suite Version, Case to Case Version and Prompt, Prompt to Prompt Version, Agent to Agent Version, Adapter to Adapter Version, Grader to Grader Version, Run to Execution Event, Run to Artifact, and Run to Score. In every case, the child table carries the foreign key, and the parent table never stores a count or a collection of its children — cardinality is always a query, never a stored fact.

**Many-to-many** appears in exactly the two places the domain genuinely has a non-ownership, many-sided association, and both are realized as their own association entities rather than as array-valued columns: Suite Version to Case Version, through Suite Composition, because a Case Version can belong to many Suite Versions and a Suite Version composes many Case Versions, and because the association itself carries meaning (ordering) worth its own row; and Case Version to Grader, through Case Grader Declaration, for the analogous reason without the ordering requirement.

**Reference-only relationships**, as opposed to ownership, appear wherever a table points to another table whose lifecycle it does not control: Run to Case Version, Prompt Version, Agent Version, Adapter Version, and Suite Version; Score to Grader Version; Suite Composition to Case Version; Case Grader Declaration to Grader. In every one of these, the referenced table's own removal (where ever legitimate at all, per Database Design's deletion philosophy) is never cascaded from the referencing side, and the referencing side's removal never cascades toward the referenced table either — the two lifecycles are genuinely independent, connected only by an immutable pointer.

**Version pinning** is the relationship shape unique to Run: five separate reference-only foreign keys (Case Version, Prompt Version, Agent Version, Adapter Version, and, where applicable, Suite Version), all fixed at Run creation and never altered afterward, together constituting the "fully specified" property the Domain Model requires. This is not a single generic "references a version" relationship reused five times incidentally — it is five independently meaningful pins, each answering a different question about what could have influenced the Run's outcome, and each therefore modeled as its own explicit foreign key rather than collapsed into a single polymorphic reference that would blur which axis had actually changed between two Runs being compared.

## Version Tables

Every versioned entity in this schema — Suite, Case, Prompt, Agent, Adapter, Grader — follows the identical two-table pattern established in Schema Philosophy, and this section names the shared shape once rather than repeating it across six sets of nearly identical table specifications.

**Stable identity.** The first table (Suite, Case, Prompt, Agent, Adapter, or Grader) exists to give the entity a persistent handle that remains meaningful across its entire revision history — the thing a user recognizes and selects by name, the thing other tables reference when they mean "this Suite" in the general sense rather than "this specific revision of it."

**Immutable versions.** The second table (Suite Version, Case Version, Prompt Version, Agent Version, Adapter Version, Grader Version) holds a specific, frozen revision's actual content or configuration. Every field on a version table, without exception, is fixed at the moment that row is written.

**Current version resolution.** This schema deliberately does not store a "current version" pointer as a mutable field on the stable-identity table. A mutable "latest version" foreign key would itself be an update to a supposedly stable row every time a new version is published, and — more importantly — would create exactly the kind of implicit, time-dependent resolution Database Design's Entity Relationships section warned against: a query resolving "the current Suite" by following that pointer would silently return a different answer depending on when it ran, which is precisely wrong for a system whose entire point is that historical references remain stable. Instead, "current version" is a derived fact — the most recently created, published version row for a given stable identity, determined by querying the version table itself (ordered by creation or by lineage) at read time. This keeps the stable-identity table genuinely immutable in the fields that matter and keeps "what's current" an interpretation applied at read time rather than a fact baked into storage that every write must keep synchronized.

**Lineage.** Each version row carries a reference to the version it supersedes, if any — its immediate predecessor within the same stable identity. This forms an explicit, traversable chain per entity, distinct from relying on a creation timestamp to imply order, for the reasons Database Design's Entity Relationships section already gives: an explicit predecessor reference survives ambiguity that a timestamp-based ordering would not, and it makes "what changed between this version and the one before it" a bounded, mechanical traversal rather than an inference.

**Historical references.** Every foreign key elsewhere in the schema that means "pin this specific version" — Run's five version references, Score's Grader Version reference — points to a version-table row, never to a stable-identity-table row. This is the structural guarantee that a historical reference never silently reinterprets itself as the entity evolves: the row a Run references today is exactly the row it will still reference after ten more versions of that entity have been published, because the reference was never to "the current one" in the first place.

## Execution Schema

The four tables organized directly around Run — Run itself, Execution Event, Artifact, and Score — form the schema's execution core, and their relationships to each other are worth describing together, distinct from their individual specifications above, because their combined shape is what makes the platform's central promise (a trustworthy, reconstructable record of what happened during an evaluation) actually hold.

**Run as the aggregate root.** Every fact about a specific evaluation — what happened during it (Execution Event), what large content it produced (Artifact), and how it scored (Score) — is owned by exactly one Run and references that Run directly. There is no path through this schema to reach an Execution Event, an Artifact, or a Score except through the Run that owns it; none of these three tables is independently browsable or meaningful without its owning Run as context.

**Ordering as an explicit property, not an assumption.** Execution Event's sequence position is not inferred from insertion order, row identifier generation order, or timestamp precision — it is an explicit field the application assigns and the schema stores, because none of those implicit alternatives can be trusted to remain correct under the concurrent-writer conditions the Backend Architecture's execution flow describes (multiple events potentially being recorded in close succession, with delivery and processing timing that the database does not control).

**Append-only behavior as a schema-wide property of this group, not a table-by-table coincidence.** Run's status field is the sole legitimate mutation across this entire four-table group; every other field on every one of these four tables, once written, is permanent. This uniformity is deliberate: an engineer who understands that Execution Event rows are never updated should be able to assume the same is true of Artifact and Score without needing to check, because the platform's trustworthiness depends on this being a schema-wide guarantee, not a per-table convention that could be inconsistently applied.

**The relationship between Execution Event and Artifact.** An Execution Event may reference one or more Artifacts, for cases where its payload is too large to be practical as inline metadata — this is a reference-only relationship (an Execution Event does not own the Artifacts it references, since an Artifact's true ownership is its Run, per Table Specifications above), which matters because it means an Artifact's existence and retention are governed entirely by its Run, never incidentally tied to the specific Execution Event that happened to reference it.

**The relationship between Score and the rest of the group.** A Score is written only after a Run's execution has concluded and its Execution Events and Artifacts are therefore complete and stable — a Grader consuming a Run's record during grading is reading data that will never change out from under it, which is precisely why grading can be performed asynchronously, independently per Grader, without any coordination concern about the underlying data shifting mid-read.

## Association Tables

Suite Composition and Case Grader Declaration are the schema's only two pure association tables — entities that exist solely to represent a many-to-many relationship between two other tables, carrying no independent business meaning of their own beyond that relationship.

**Suite Composition** exists because a Suite Version's relationship to the Case Versions it composes cannot be expressed as a simple foreign key on either side: a Case Version legitimately belongs to many Suite Versions across many Suites (the same bug-fix task might appear in both a general regression suite and a language-specific suite), and a Suite Version legitimately composes many Case Versions. Beyond the raw many-to-many fact, the association itself carries meaning — the order in which Case Versions appear within a Suite Version — which is exactly the kind of relationship-level data that justifies a dedicated association entity rather than a bare join table with no fields of its own.

**Case Grader Declaration** exists for the analogous reason without the ordering dimension: a Grader is typically applicable to many Cases (an objective test-pass/fail Grader has no reason to be Case-specific), and a Case typically declares several applicable Graders. The association records a fact — "this Grader is declared applicable to this Case Version" — that is meaningful independent of any specific Run, and that a Run's eventual Scores depend on for determining which Graders to invoke in the first place.

No other many-to-many relationship exists in this schema. Every other relationship among the twenty tables specified above is either one-to-many ownership or a reference-only foreign key, which is itself worth noting: a schema with only two association tables, both explicitly justified, is far easier to reason about than one where many-to-many relationships have proliferated informally, and keeping that count low and deliberate is treated here as a property worth actively preserving as the schema evolves.

## Constraints

**Uniqueness.** Every stable-identity table's natural identifying attribute (a Suite's name within its Project, a Case's name within its Project) is expected to be unique within its owning scope, so that two indistinguishable entities cannot coexist in a way that would confuse anyone selecting between them. Every version table's version identifier is unique within its owning stable-identity table. Score's Run-and-Grader-Version pairing is unique, per Table Specifications above, which is the constraint that makes idempotent grading-task redelivery safe.

**Ownership.** Every table specified as "owned by" another in this document requires a valid, non-null reference to that owner at all times — an owned row can never exist in an orphaned state, whether at creation or at any point afterward, since the owning relationship is exactly what defines the owned row's reason for existing.

**Required references.** Every reference-only foreign key described in Relationship Model is similarly required and must resolve to a valid row at the moment it is written — Run's five pinned version references, Score's Grader Version reference, and both association tables' pair of references are never permitted to be null or dangling, because an unresolvable reference would silently undermine exactly the historical reproducibility this schema exists to guarantee.

**Version pinning.** Once written, none of Run's five version references may ever be changed to point to a different version row — this is not merely a convention but a constraint this schema treats as inviolable, since a Run whose pinned versions could be altered after creation would no longer satisfy the Domain Model's Run Created event, which fixes those references for all time.

**Append-only rules.** Every table identified in Table Specifications as immutable after creation — every version table, Execution Event, Artifact, Score, Audit Log, and both association tables — permits no update operation against any field of an existing row, under any application code path, in normal operation. Run is the schema's sole partial exception, permitting exactly one field (status) to advance forward through a finite, validated set of transitions, and no other field of an existing Run row is ever a legitimate update target.

**Lifecycle rules.** An Execution Event or Artifact can only be created while its owning Run is in an active (non-terminal) execution state. A Score can only be created while its owning Run is in its grading phase or has reached a terminal state carrying partial-grading metadata. A Run's status can only transition according to the finite state machine the Domain Model defines — never to an arbitrary status value, and never backward from a terminal state.

## Derived Data

This schema deliberately does not store several categories of data that could, at first glance, seem convenient to persist directly, and this section names them explicitly because the temptation to add them will recur as the platform is implemented and later extended.

**Counts and aggregates are not stored as fields.** A Suite's number of composed Cases, a Case's number of historical Runs, a Run's number of recorded Execution Events, a Grader's number of Scores produced — none of these are columns on any table in this schema. Each is a query against the owning relationship, computed at read time. Storing any of them as a denormalized counter field would introduce exactly the kind of duplicated fact Database Design's Normalization Philosophy warns against: a second place the true count could drift from, requiring either a triggered update on every insert to the owned table (adding write-path complexity and lock contention to the schema's highest-volume tables, for a value that is nearly always cheap to compute on demand) or, worse, a count that silently goes stale.

**Statistics and trend figures are not stored as fields.** A Suite's current pass rate, an Agent's average cost per Run, a Case's historical difficulty score — all of these are computed from the underlying Run and Score history at query time, or, where query-time computation genuinely becomes too expensive at scale, by an explicitly named materialized read model (see Read Models below), never by a field on Suite, Agent, or Case that some background process is responsible for keeping in sync. The distinction matters: a materialized read model is an explicit, named, rebuildable artifact whose staleness characteristics are understood and accepted; a quietly-added "cached" column on a core entity table is an implicit one whose staleness is easy to overlook until it causes a real discrepancy in a regression-detection decision.

**The general principle.** Any field that can be correctly and unambiguously computed from data this schema already stores elsewhere should not also be stored directly, because every such field is a second source of truth for a fact that already has one, and Database Design's Normalization Philosophy treats a second source of truth as a defect to be avoided by default, not a convenience to be adopted casually. The exceptions — where a value genuinely needs to be captured because it cannot be recomputed later, such as a Run's execution-cost facts (token usage, wall-clock time, compute consumed), which are observed once during execution and are not derivable from anything else this schema stores after the fact — are captured directly on Run precisely because they are not derived data at all; they are primary facts with no other source.

## Read Models

Everything specified in Table Specifications above is normalized schema — the single, authoritative source of truth this document exists to define. Nothing in this document describes a materialized view, a precomputed rollup, or any other denormalized structure, and that omission is deliberate rather than incomplete.

The normalized schema is where every fact is written and where every fact's correctness is guaranteed by the constraints in this document. A future materialized or otherwise denormalized read model — built to serve a specific dashboard query pattern that query-time computation over the normalized schema cannot serve fast enough, per Database Design's Indexing Philosophy — is always built as a derivative of this schema, rebuildable from it at any time, and never becomes a place where a fact is written first or written independently. If a future read model and the normalized schema ever disagree, the normalized schema is correct by definition, and the read model is stale and due for a rebuild — this is the same relationship Database Design already establishes between the system of record and any future analytics warehouse, restated here as a boundary this document holds firm: schema design defines the source of truth; read-model design, wherever it eventually happens, is a separate concern layered on top of it, not a modification to it.

## Schema Evolution

New entities are added to this schema the same way the Domain Model's Extensibility Model already anticipates domain concepts growing: as new tables following the established patterns, never as a restructuring of tables that already exist. A new kind of Case (a new task category) requires no new table at all, since Case Version's content is already generic. A new kind of Artifact requires no new table, for the identical reason. A new Agent requires one new Agent row and one new Adapter row, following the exact shape every existing Agent and Adapter already follows — not a schema change, an instance of the existing schema.

Where a genuinely new concept does require a new table — a future Grader SDK's registration metadata, for instance — it is added following the same ownership and versioning patterns established here: a clear statement of what it is identified by, what owns it, what it references, and whether it is versioned, mutable, or append-only, exactly as every table in this document is specified. Backward compatibility for existing historical data is preserved automatically whenever a new table is purely additive — existing Runs, Scores, and version rows are never restructured to accommodate a new table, because nothing about a new table's existence requires touching a row that predates it.

The one category of change this schema actively resists is altering the *meaning* of an existing field on an already-populated table — changing what a status value represents, redefining what a foreign key on an existing table points to. Where the business genuinely requires this kind of change, the correct pattern, consistent with every versioning decision in this document, is to introduce a new version or a new table capturing the new meaning, leaving historical rows interpretable exactly as they were at the time they were written, rather than reinterpreting them retroactively through a redefined field.

## Future Extensions

**Multi-tenancy.** Every table in this schema is already scoped to Project, directly or transitively (through the definitional entities and, for Run, through its pinned Case Version). A future organization or tenancy layer sits above Project, exactly as the Backend Architecture and Database Design both anticipate, requiring one new table (an organization or tenant entity) and one new reference on Project — not a restructuring of anything specified in this document.

**Grader SDK and Adapter SDK.** Both are anticipated as formalizations of an already-modular contract, per the Domain Model's Extensibility Model — a Grader SDK's registration metadata, or an Adapter SDK's equivalent, is new, purely additive table structure describing how a Grader or Adapter is registered and discovered, layered on top of the existing Grader, Grader Version, Adapter, and Adapter Version tables without altering what those tables mean or how they relate to Score and Run.

**Plugin tables generally.** Any future plugin-style extension — a new category of grading capability, a new kind of agent integration — follows the same pattern: new tables, following this document's established ownership and versioning conventions, referencing the existing schema without modifying it.

**Warehouse integration.** As Database Design's Scalability section anticipates, this schema's normalized, partitioned, append-only tables are designed to migrate cleanly into a future analytics warehouse's ingestion model. Nothing in this document needs to change to support that eventual integration — the warehouse would consume this schema's tables as its source, following the same read-model relationship described above, applied at a larger scale.

None of these extensions requires altering the aggregate boundaries, ownership rules, or versioning pattern established in this document. That is the actual test this schema was designed against, consistent with every architecture document that precedes it: whether five years of real growth can be absorbed by adding tables and references, or whether it would require rewriting ones that already exist. Every extension named above satisfies the former.

## References

- System Overview (`docs/architecture/system-overview.md`)
- Domain Model (`docs/architecture/domain-model.md`)
- ADR-0001: Foundational System Architecture (`docs/adr/ADR-0001-system-architecture.md`)
- Backend Architecture (`docs/architecture/backend-architecture.md`)
- Database Design (`docs/architecture/database-design.md`)