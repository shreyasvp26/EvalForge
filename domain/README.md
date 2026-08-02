# agent-eval-domain

Pure Domain Layer for EvalForge.

## Why

Per Backend Architecture §5 / §11 and the Domain Model document, this package is the
long-term source of truth for business concepts. It has **zero** dependencies on
HTTP, ORM, queues, adapters, graders, or any other module outside `shared`
(error base types and tiny helpers only).

## Bounded contexts

| Package                 | Owns                                                                          |
| ----------------------- | ----------------------------------------------------------------------------- |
| `evaluation_management` | Project, Suite, Case, Prompt                                                  |
| `execution`             | Run, Execution Event, Artifact, Score, Sandbox, Execution Engine concept, NDM |
| `agent_integration`     | Agent, Adapter                                                                |
| `grading`               | Grader                                                                        |
| `versioning`            | Version status, lineage helpers                                               |

## Rules

- Domain never reads configuration or logs.
- Invariants are enforced in aggregate methods; violations raise typed domain errors.
- Repository interfaces are defined here; Infrastructure implements them later.
- Prefer frozen value objects; mutate aggregates only through explicit methods.
