# ADR-0002: Application Layer ports and Unit of Work

## Status

Accepted

## Context

Backend Architecture §4–§8 assigns the Application Layer ownership of use-case
orchestration, transaction boundaries, Project-scoped authorization, and
idempotency of use-case invocation. Domain already defines repository
Protocols. Persistence, messaging, and auth policy implementations do not
exist yet (Infrastructure phase).

## Decision

1. **Unit of Work** is an Application port that exposes Domain repository
   Protocols and `commit` / `rollback`. Application use cases open one UoW per
   invocation, mutate aggregates, commit, then dispatch domain events.
2. **Domain event dispatch**, **run queue**, **authorization**, and
   **idempotency store** are Application-owned ports. Infrastructure will
   implement them (including transactional outbox if required). Application
   never imports concrete brokers, ORMs, or HTTP frameworks.
3. **ID generation** is an Application concern (stdlib UUID default). Domain
   only requires non-empty opaque IDs.
4. **Domain errors** are translated at the Application boundary into
   Application-layer errors (`NotFoundApplicationError`,
   `DomainTranslationError`, …) so API/Workers never need to import Domain
   exception types to classify failures.
5. Use cases are explicit classes with constructor-injected ports and an
   `execute(command|query)` method — no framework base classes.

## Consequences

- API and Workers depend on Application only for writes and authorized reads.
- Infrastructure can swap PostgreSQL / Redis / queue implementations without
  changing use cases.
- Application unit tests mock ports exclusively; they verify orchestration,
  not persistence.
