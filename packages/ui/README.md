# `@agent-eval/ui`

EvalForge design system: tokens and reusable UI primitives.

## Ownership

This package owns:

- Design tokens (CSS variables)
- Typography primitives (`Heading`, `Text`)
- Motion primitives
- Form controls, tables, feedback, overlays, charts
- `<Icon />` wrapper and curated Lucide re-exports

It must **never** contain EvalForge domain components (`RunCard`, `ProjectCard`, `ScorePanel`, etc.). Those live in `apps/web`.

See [docs/design/design-principles.md](../../docs/design/design-principles.md) and [ADR-0003](../../docs/adr/ADR-0003-frontend-design-system.md).

## Usage

```ts
import { cn, Heading, Text, Icon, Search } from "@agent-eval/ui";
import "@agent-eval/ui/styles.css";
```

## Fonts

Geist Sans / Geist Mono are loaded in `apps/web` via `geist/font` and expose `--font-geist-sans` / `--font-geist-mono`. Tokens reference those variables.

## Storybook

```bash
pnpm --filter @agent-eval/ui storybook
```

Storybook is the engineering playground. The product-facing gallery lives at `/design-system` in `apps/web`.

## Status

Phase 15A — foundation complete (tokens, primitives, Storybook). Product CRUD is out of scope.
