# `@agent-eval/web`

EvalForge web application — Next.js App Router.

## Status

- **Phase 15A** — design system foundation — **complete**
- **Phase 15B** — product UX foundation — **complete**

No product CRUD or API-backed feature screens yet.

## Scripts

```bash
pnpm --filter @agent-eval/web dev      # http://localhost:3000
pnpm --filter @agent-eval/web build
pnpm --filter @agent-eval/web start
pnpm --filter @agent-eval/web typecheck
```

## Architecture

| Area            | Path                             |
| --------------- | -------------------------------- |
| App shell / nav | `src/components/shell/`          |
| Product layouts | `src/components/layouts/`        |
| UX patterns     | `src/components/patterns/`       |
| Design gallery  | `src/app/(shell)/design-system/` |
| Routes          | `src/app/(shell)/…`              |

- Consumes `@agent-eval/ui` for tokens and primitives
- Prefer Server Components; `"use client"` at the smallest leaf
- Lazy-load command palette

## Keyboard (shell)

| Shortcut         | Action                   |
| ---------------- | ------------------------ |
| ⌘K / Ctrl+K      | Command palette          |
| G then P / R / A | Projects / Runs / Agents |
| ?                | Shortcuts cheatsheet     |
| Esc              | Close overlays           |

## Docs

- [Design principles](../../docs/design/design-principles.md)
- [Developer guidelines](../../docs/design/developer-guidelines.md)
- [Layouts](../../docs/design/layouts.md) · [Patterns](../../docs/design/product-patterns.md) · [Navigation](../../docs/design/navigation.md) · [DataGrid](../../docs/design/data-grid.md)
- [ADR-0003](../../docs/adr/ADR-0003-frontend-design-system.md)
