# ADR-0003: Frontend Design System

## Status

Accepted

## Date

2026-08-02

## Context

Phase 14 completed the production-hardened backend. Phase 15 begins the presentation plane. `apps/web` is still a Phase 0 TypeScript scaffold with no UI framework. Before any product screens exist, the frontend needs an intentional design system and shell architecture. Without an ADR, early pages would invent local patterns — spacing, type sizes, navigation chrome — that are expensive to reconcile later.

EvalForge's domain is hierarchical (Projects → Suites → Cases → Runs) and trace-heavy (events, artifacts, scores). The UI must stay dense, keyboard-first, and calm. The backend owns product truth (ADR-0001); the frontend is a renderer. That still leaves open: where tokens and primitives live, how the app chrome is structured, and how engineers discover components.

## Decision

### Hybrid package boundary

- **`packages/ui` (`@agent-eval/ui`)** owns design tokens, typography primitives (`Heading`, `Text`), motion primitives, form controls, tables, feedback, overlays, charts, and the `<Icon />` wrapper.
- **`apps/web` (`@agent-eval/web`)** owns the application shell, navigation, sidebar, top bar, command palette, product layouts (including opt-in inspector), feature composition, and the product-facing `/design-system` gallery.

`packages/ui` must never contain EvalForge-specific domain components (`RunCard`, `ProjectCard`, `AgentCard`, `ScorePanel`, etc.). Those belong only in `apps/web`.

### Application shell: sidebar + top bar

Every authenticated product view sits inside a left sidebar + top bar shell. The sidebar represents the product hierarchy (Projects → Suites → Cases → Runs). A right **inspector** is provided as a **layout primitive** that pages opt into (e.g. Run Details, Artifact Viewer), not as permanent chrome on every route.

### Dual documentation surfaces

- **Storybook** in `packages/ui` is the engineering playground for reusable components (variants, states, a11y).
- **`/design-system`** in `apps/web` is the product-facing gallery of principles, tokens, and curated examples inside the real shell.

### Typography and icons

Product code uses semantic `<Heading>` / `<Text>` components and the `<Icon />` wrapper. Raw heading/paragraph styling and direct `lucide-react` imports in `apps/web` are forbidden.

### Theme and stack

Next.js App Router, TypeScript strict, Tailwind with CSS-variable tokens, calm blue-gray accent, Geist Sans + Geist Mono, light/dark via class strategy (system default). shadcn/Radix only as low-level primitives restyled to EvalForge tokens. Framer Motion only for layout/presence/dialogs; CSS for simple transitions. Prefer Server Components; lazy-load heavy overlays.

### Design principles document

[`docs/design/design-principles.md`](../design/design-principles.md) is the single source of truth for philosophy, tokens, motion, accessibility, and anti-patterns. Future frontend ADRs may refine it; drive-by contradictions in PRs are rejected.

## Consequences

### Easier

- Consistent import paths and ownership for every future page
- Reusable primitives without leaking domain into a shared package
- Keyboard-first shell and command palette established before CRUD
- Engineers have Storybook; product review has `/design-system`

### Harder / costs

- Two packages to wire and version in the monorepo
- Discipline required: domain UI must not "temporarily" land in `packages/ui`
- Inspector-as-opt-in means each detail view must choose a layout deliberately
- Stricter typography/icon rules require components before first screens

### Non-goals (Phase 15A)

No CRUD pages, dashboards, auth product flows, or API-backed business screens. Foundation only.
