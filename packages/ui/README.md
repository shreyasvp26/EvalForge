# `@agent-eval/ui`

EvalForge design system: tokens and reusable UI primitives.

## Ownership

This package owns:

- Design tokens (`src/styles/tokens.css` → `@agent-eval/ui/styles.css`)
- Typography (`Heading`, `Text`)
- `Icon` + curated Lucide re-exports
- Form controls, feedback, overlays, table primitives
- `DataGrid` (TanStack Table) + search / column visibility / pagination helpers
- Generic layout: `Stack`, `Cluster`, `Container`, `Panel`, `InspectorLayout`
- Motion helpers (`FadeIn`, `Presence`)
- Storybook (including docs MDX and stories from `apps/web` patterns/shell)

It must **never** contain EvalForge domain components (`RunCard`, `ProjectCard`, `ScorePanel`, etc.). Those live in `apps/web`.

## Usage

```ts
import { cn, Button, DataGrid, Heading, Icon, Search, Text } from "@agent-eval/ui";
import "@agent-eval/ui/styles.css";
```

## Fonts

Geist Sans / Geist Mono are loaded in `apps/web` via `geist/font` (`--font-geist-sans` / `--font-geist-mono`). Tokens reference those variables.

## Storybook

```bash
pnpm --filter @agent-eval/ui storybook
```

Includes documentation pages under **Docs/** and component stories. Product gallery: `/design-system` in `apps/web`.

## Docs

- [Design principles](../../docs/design/design-principles.md)
- [Developer guidelines](../../docs/design/developer-guidelines.md)
- [DataGrid](../../docs/design/data-grid.md)
- [ADR-0003](../../docs/adr/ADR-0003-frontend-design-system.md)

## Status

Phases 15A–15B foundation. Product CRUD is out of scope for this package.
