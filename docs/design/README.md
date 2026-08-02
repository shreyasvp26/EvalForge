# EvalForge Design

Frontend design documentation — visual language, ownership, and contribution rules.

| Document                                             | Purpose                                                          |
| ---------------------------------------------------- | ---------------------------------------------------------------- |
| [design-principles.md](./design-principles.md)       | Philosophy, tokens, motion, a11y, anti-patterns — **read first** |
| [developer-guidelines.md](./developer-guidelines.md) | Contributor guide (imports, ownership, verify)                   |
| [layouts.md](./layouts.md)                           | AppShell, PageLayout, DetailLayout, SplitView, …                 |
| [product-patterns.md](./product-patterns.md)         | Skeletons, empty/error/confirm patterns                          |
| [navigation.md](./navigation.md)                     | Sidebar, ⌘K, shortcuts, breadcrumbs                              |
| [data-grid.md](./data-grid.md)                       | TanStack DataGrid                                                |

Related:

- [ADR-0003: Frontend Design System](../adr/ADR-0003-frontend-design-system.md)
- Product gallery: `/design-system` in `apps/web`
- Engineering playground: `pnpm --filter @agent-eval/ui storybook`

## Ownership

| Concern                                               | Location                         |
| ----------------------------------------------------- | -------------------------------- |
| Tokens, primitives, DataGrid, generic layout          | `packages/ui` (`@agent-eval/ui`) |
| Shell, navigation, product layouts/patterns, features | `apps/web` (`@agent-eval/web`)   |

`packages/ui` must never contain EvalForge domain components (`RunCard`, `ProjectCard`, `ScorePanel`, etc.).
