# Frontend developer guidelines

Companion to [design-principles.md](./design-principles.md). Follow these when implementing UI in this monorepo.

## Package ownership

| Put it in `@agent-eval/ui`                  | Put it in `apps/web`              |
| ------------------------------------------- | --------------------------------- |
| Tokens, `Heading` / `Text` / `Icon`         | App shell, sidebar, top bar       |
| Forms, tables, overlays, feedback           | Command palette, product layouts  |
| Generic layout (`Stack`, `InspectorLayout`) | Feature composition, domain cards |
| Storybook stories for the above             | `/design-system` product gallery  |

**Never** add `RunCard`, `ProjectCard`, `AgentCard`, `ScorePanel`, or other domain UI to `packages/ui`.

## Imports

```tsx
// ✅
import { Button, Heading, Icon, Search, Text } from "@agent-eval/ui";

// ❌
import { Search } from "lucide-react";
import { h1 } from "..."; // style raw headings in product code
```

- Product copy uses `<Heading>` / `<Text>` only.
- Icons use `<Icon icon={Search} />` with icons re-exported from `@agent-eval/ui`.
- Prefer semantic spacing (`Stack` / `Cluster` / scale tokens) over arbitrary `p-[13px]`.

## Storybook vs `/design-system`

| Surface                       | Audience                | Content                                                     |
| ----------------------------- | ----------------------- | ----------------------------------------------------------- |
| Storybook (`packages/ui`)     | Engineers               | Every reusable component: variants, disabled, loading, a11y |
| `/design-system` (`apps/web`) | Product / design review | Curated tokens + principles inside the real shell           |

New `packages/ui` components **must** ship with basic Storybook stories.

## Server vs client

- Default to Server Components in `apps/web`.
- Add `"use client"` only at the leaf that needs state, browser APIs, or event handlers.
- Lazy-load heavy overlays (command palette, large dialogs) with `next/dynamic`.

## Accessibility checklist

- [ ] Keyboard operable
- [ ] Visible `focus-visible`
- [ ] Meaningful `aria-label` on icon-only controls
- [ ] Light and dark contrast OK (WCAG AA)
- [ ] Respects `prefers-reduced-motion` for non-essential motion

## Verify before commit

```bash
pnpm verify
```

Use Conventional Commits. Push only after verify passes.
