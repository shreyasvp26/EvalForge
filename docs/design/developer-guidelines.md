# Frontend developer guidelines

Companion to [design-principles.md](./design-principles.md). This is the **contributor guide** for anyone extending the EvalForge frontend (Phases 15A–15B).

Also read:

| Doc                                                   | Topic                                            |
| ----------------------------------------------------- | ------------------------------------------------ |
| [layouts.md](./layouts.md)                            | AppShell, PageLayout, DetailLayout, SplitView, … |
| [product-patterns.md](./product-patterns.md)          | Skeletons, empty/error/confirm patterns          |
| [navigation.md](./navigation.md)                      | Sidebar, ⌘K, shortcuts, breadcrumbs              |
| [data-grid.md](./data-grid.md)                        | TanStack DataGrid usage                          |
| [ADR-0003](../adr/ADR-0003-frontend-design-system.md) | Hybrid package boundary                          |

---

## Package ownership

| Put it in `@agent-eval/ui` (`packages/ui`)            | Put it in `apps/web`                                          |
| ----------------------------------------------------- | ------------------------------------------------------------- |
| Design tokens (CSS variables)                         | `AppShell`, sidebar, top bar, command palette                 |
| `Heading`, `Text`, `Icon` + Lucide re-exports         | Product layouts (`PageLayout`, `PageHeader`, …)               |
| Primitives: Button, Input, Dialog, Table, …           | Product UX patterns (`PageSkeleton`, `ConfirmationDialog`, …) |
| Generic layout: `Stack`, `Cluster`, `InspectorLayout` | Feature composition and domain UI                             |
| `DataGrid` and related helpers                        | `/design-system` gallery                                      |
| Storybook stories for the above                       | Route pages under `src/app`                                   |

### Never put in `packages/ui`

- `RunCard`, `ProjectCard`, `AgentCard`, `ScorePanel`, `SuiteTable`, …
- Anything that imports API clients, React Query feature hooks, or domain DTOs
- EvalForge-branded empty states that name Projects/Runs as _product entities_ (prefer composing generic `EmptyState` / patterns in `apps/web`)
- Navigation chrome that knows about “Workspace → Suites → Cases”

**Rule of thumb:** if the component’s name is a domain noun, it belongs in `apps/web`.

---

## Design system quick reference

### Tokens & theme

- Colors, radii, spacing, motion, and status semantics live in `packages/ui/src/styles/tokens.css` as `--ef-*` CSS variables.
- Light / dark via `.dark` class; `next-themes` in `apps/web` (`attribute="class"`, default `system`).
- Accent (calm blue-gray) should stay under ~10% of any viewport.

### Typography

- Fonts: Geist Sans + Geist Mono (loaded in `apps/web` root layout).
- Product UI uses `<Heading>` / `<Text>` only — no ad-hoc `text-lg` / raw styled `<h1>` / `<p>`.
- Roles: Display, Page, Section, Card, Body, Secondary, Caption, Code, Table.

### Spacing

Scale only: `4 · 8 · 12 · 16 · 24 · 32 · 48 · 64` (via `Stack` / `Cluster` gap props or tokenized utilities).

### Motion

- Prefer CSS 150–250ms transitions.
- Framer Motion only for presence / dialogs / layout.
- Every animation must answer where-from, where-to, or what-changed.
- Honor `prefers-reduced-motion`.

### Accessibility

WCAG AA: keyboard, focus-visible, labels, contrast, landmarks, reduced motion.

---

## Imports

```tsx
// ✅
import { Button, DataGrid, Heading, Icon, Search, Text } from "@agent-eval/ui";
import { PageLayout, PageHeader } from "@/components/layouts";
import { ConfirmationDialog } from "@/components/patterns";

// ❌
import { Search } from "lucide-react";
<h1 className="text-2xl">…</h1>;
```

---

## How to add a UI primitive (`packages/ui`)

1. Implement under `packages/ui/src/components/…` using tokens + `cn`.
2. Export from `packages/ui/src/index.ts`.
3. Add Storybook stories (default, disabled/loading, dark via backgrounds).
4. Keep it domain-agnostic.
5. Run `pnpm verify`.

## How to add a product component (`apps/web`)

1. Prefer composing layouts + patterns + `@agent-eval/ui`.
2. Place under `components/layouts`, `components/patterns`, `components/shell`, or a future `features/…`.
3. Default to Server Components; `"use client"` at the smallest leaf.
4. Add gallery coverage on `/design-system` when the pattern is reusable.
5. Pattern stories for Storybook live under `apps/web/src/components/**` and are picked up by the ui Storybook config.
6. Run `pnpm verify`.

---

## Storybook vs `/design-system`

| Surface                                              | Audience                | Content                                               |
| ---------------------------------------------------- | ----------------------- | ----------------------------------------------------- |
| Storybook (`pnpm --filter @agent-eval/ui storybook`) | Engineers               | Exhaustive variants, a11y addon, MDX docs pages       |
| `/design-system`                                     | Product / design review | Curated principles + live demos inside the real shell |

---

## Server vs client

- Prefer RSC in `apps/web`.
- Lazy-load heavy overlays (`next/dynamic` for command palette).
- Persist UI prefs (sidebar) in `localStorage` via small client hooks — never block SSR on them.

---

## Accessibility checklist

- [ ] Keyboard operable end-to-end
- [ ] Visible `focus-visible`
- [ ] `aria-label` on icon-only controls
- [ ] Light + dark contrast (including status badges)
- [ ] `prefers-reduced-motion` respected
- [ ] Dialogs/drawers trap focus and restore it

---

## Verify & commits

```bash
pnpm verify
```

Conventional Commits, e.g. `feat(web): …`, `feat(ui): …`, `docs(design): …`.  
Push only after verify passes.
