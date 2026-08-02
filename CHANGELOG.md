# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Phase 0 repository foundation (monorepo, tooling, CI scaffolding)
- Engineering foundation: shared TS packages (`errors`, `env`, `logger`, `utils`), Python `shared/`, Vitest/pytest, Husky, root verify scripts
- Domain Layer: pure Python aggregates, versioning, Run lifecycle, NDM, repository ports, unit tests
- Application Layer: use cases, Unit of Work / event / queue / auth ports, DTOs, Domain error translation, orchestration unit tests
- Infrastructure Layer: package scaffold (`agent-eval-infrastructure`) colocated with existing Docker/ops assets
- Infrastructure SQLAlchemy foundation: Engine, Session factory, declarative Base, naming conventions, Schema Design ORM models, repository base (no repository methods yet)
