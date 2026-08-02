# `@agent-eval/web`

EvalForge web application — Next.js App Router.

## Status

Phase 15A — frontend foundation complete (design system, shell, `/design-system` gallery). No product CRUD yet.

## Scripts

```bash
pnpm --filter @agent-eval/web dev      # http://localhost:3000
pnpm --filter @agent-eval/web build
pnpm --filter @agent-eval/web start
pnpm --filter @agent-eval/web typecheck
```

## Architecture

- Consumes `@agent-eval/ui` for tokens and primitives
- Owns app shell, navigation, command palette, product layouts, `/design-system`
- Prefer Server Components; keep client islands small

See [docs/design/design-principles.md](../../docs/design/design-principles.md) and [ADR-0003](../../docs/adr/ADR-0003-frontend-design-system.md).
