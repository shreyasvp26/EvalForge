# EvalForge Design

Frontend design documentation for EvalForge. This is the source of truth for visual language, interaction quality, and component ownership.

| Document                                             | Purpose                                                               |
| ---------------------------------------------------- | --------------------------------------------------------------------- |
| [design-principles.md](./design-principles.md)       | Philosophy, tokens, motion, a11y, anti-patterns — **read this first** |
| [developer-guidelines.md](./developer-guidelines.md) | How to implement UI in this monorepo                                  |

Related:

- [ADR-0003: Frontend Design System](../adr/ADR-0003-frontend-design-system.md)
- Product gallery: `/design-system` in `apps/web`
- Engineering playground: Storybook in `packages/ui`

## Ownership

| Concern                                                           | Location                         |
| ----------------------------------------------------------------- | -------------------------------- |
| Design tokens, primitives, forms, tables, overlays, charts, icons | `packages/ui` (`@agent-eval/ui`) |
| App shell, navigation, command palette, product layouts, features | `apps/web` (`@agent-eval/web`)   |

`packages/ui` must never contain EvalForge domain components (`RunCard`, `ProjectCard`, `ScorePanel`, etc.).
