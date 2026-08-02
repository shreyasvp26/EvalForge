# EvalForge Design Principles

**Status:** Accepted (Phase 15A)  
**Audience:** Anyone writing frontend code for EvalForge  
**Role:** Single source of truth for visual language, interaction quality, and UX standards

If a PR conflicts with this document, the PR is wrong unless an ADR updates this document first.

---

## 1. Design philosophy

EvalForge is infrastructure for evaluating coding agents. The UI should feel like a tool senior engineers trust — closer to Linear, GitHub, Raycast, Arc, Warp, and Height than to a marketing site or a generic admin template.

### We aim for

- **Minimal** — every element earns its place
- **Elegant** — quiet confidence, not decoration
- **Calm** — nothing screams; status color is meaning, not mood
- **Dense but never cluttered** — information-rich without noise
- **Fast** — perceived performance matters as much as measured
- **Keyboard-first** — the mouse is optional for power users
- **Invisible chrome** — the user's work (runs, traces, scores) is the focus

### We reject

- Generic Tailwind dashboards
- Default shadcn / Radix skin with no opinion
- Vercel clones and Dribbble concepts
- "AI-generated" / vibe-coded admin panels
- Neon AI gradients, glassmorphism, oversized radii, floating card grids
- Decorative charts and hero illustrations

Whitespace is intentional. Typography does the heavy lifting. Motion is restrained. Hierarchy is obvious.

---

## 2. Package ownership

| Owns                                                                                                                                                                           | Does not own                                                                 |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------- |
| **`packages/ui` (`@agent-eval/ui`)** — tokens, typography, icons, form controls, tables, **DataGrid**, feedback, overlays, generic layout (`Stack`, `InspectorLayout`), motion | EvalForge domain UI (`RunCard`, `ProjectCard`, `AgentCard`, `ScorePanel`, …) |
| **`apps/web` (`@agent-eval/web`)** — AppShell, navigation, product layouts (`PageLayout`, …), UX patterns, feature composition, `/design-system` gallery                       | Low-level token definitions duplicated from ui                               |

**Rule:** if a component names a domain concept, it belongs in `apps/web`. If it could ship in any serious product unchanged, it belongs in `packages/ui`.

### Dual documentation surfaces

| Surface                           | Audience                | Purpose                                                                                    |
| --------------------------------- | ----------------------- | ------------------------------------------------------------------------------------------ |
| **Storybook** (`packages/ui`)     | Engineers               | Docs MDX + interactive playground — variants, states, a11y                                 |
| **`/design-system`** (`apps/web`) | Product / design review | Curated gallery of tokens, principles, and representative components inside the real shell |

Do not turn `/design-system` into a second Storybook. Keep it curated. Put exhaustive variant matrices in Storybook.

---

## 3. Color system

### Neutral-first

The interface is almost monochrome. Surfaces, text, borders, and muted fills do most of the work. Accent color occupies **less than ~10%** of any viewport.

Accent: calm **blue-gray** — professional, quiet, never neon.

### Semantic status colors

Use semantic tokens only for meaning. Do not invent one-off colors.

| Token role  | Meaning                                                           |
| ----------- | ----------------------------------------------------------------- |
| `success`   | Passed, healthy, completed successfully                           |
| `warning`   | Degraded, attention needed, flaky                                 |
| `danger`    | Failed, blocked, destructive                                      |
| `running`   | In progress                                                       |
| `queued`    | Waiting to start                                                  |
| `cancelled` | User or system cancelled                                          |
| `completed` | Terminal success path (distinct from generic success when needed) |
| `grading`   | Grader pipeline in progress                                       |

Status color must remain legible in light and dark mode at WCAG AA for text/icon on its surface.

### Theme

- Default: **system preference**
- Explicit light / dark toggle in the shell
- Tokens are CSS variables; components consume tokens, never hard-coded hex in product code

---

## 4. Typography

Typography is the primary design tool. Use a **semantic scale**, not arbitrary Tailwind font sizes.

### Fonts

- **Geist Sans** — UI and prose
- **Geist Mono** — code, IDs, logs, traces, tabular data where alignment matters

### Semantic components (required)

Product code must use:

- `<Heading>` — for titles (with a `level` / `variant`)
- `<Text>` — for body, secondary, caption, code-adjacent copy

**Do not** use raw `<h1>`–`<h6>` or `<p>` for product UI styling. Semantic HTML may be rendered _by_ these components (they map variants to the correct element).

### Scale (roles)

| Role          | Use                                                                 |
| ------------- | ------------------------------------------------------------------- |
| Display       | Rare marketing-adjacent moments only (gallery, empty brand moments) |
| Page title    | Top of a primary view                                               |
| Section title | Major sections within a page                                        |
| Card title    | Titles inside quiet bordered regions                                |
| Body          | Default reading text                                                |
| Secondary     | Supporting copy, less emphasis                                      |
| Caption       | Metadata, timestamps, helper text                                   |
| Code          | Inline code and mono labels                                         |
| Table label   | Column headers and dense table chrome                               |

Do not sprinkle `text-lg`, `text-xl`, `text-[15px]` through feature code. If a size is missing, extend the scale in `@agent-eval/ui` and document it.

---

## 5. Spacing

Strict scale only (px):

`4 · 8 · 12 · 16 · 24 · 32 · 48 · 64`

- Prefer layout primitives (`Stack`, `Cluster`, `Container`) over one-off margins
- Avoid arbitrary values (`p-[13px]`, `gap-[22px]`)
- Density is welcome; giant empty regions are not "premium"

---

## 6. Radii

| Element        | Radius        |
| -------------- | ------------- |
| Buttons        | 8px           |
| Inputs         | 8px           |
| Cards / panels | 10px          |
| Dialogs        | 12px          |
| Badges / pills | fully rounded |

Avoid oversized rounded corners. Consistency beats novelty.

---

## 7. Borders and shadows

- Prefer **borders and spacing** over elevation
- Shadows are extremely subtle; if a shadow is clearly noticeable, it is too strong
- Cards are quiet: border + surface, not floating glass

---

## 8. Motion

Every animation must answer at least one question:

1. Where did this come from?
2. Where did this go?
3. What changed?

If none apply, remove the animation.

### Defaults

- Duration: **150–250ms**
- Prefer **CSS transitions** for hover, focus, color, opacity, simple transforms
- Use **Framer Motion** only for layout transitions, shared layout, dialogs, and presence
- Respect `prefers-reduced-motion` — reduce or disable non-essential motion
- Avoid springy "toy" physics

---

## 9. Icons

- **Lucide only**, via the `<Icon />` wrapper from `@agent-eval/ui`
- Do **not** import from `lucide-react` in `apps/web`
- Consistent default size and stroke; override deliberately, rarely

---

## 10. Component principles

### Fewer, higher quality

Prefer a small set of excellent components over a large incomplete set.

### States are first-class

Every reusable component that needs them must design for:

- Default / hover / active / focus-visible
- Disabled
- Loading (where async)
- Empty / error (for composite patterns like tables)
- Dark and light
- Keyboard operation
- Responsive behavior appropriate to the control

### Tables are product-critical

Tables are not generic HTML. Support sorting, filtering hooks, empty/loading states, row actions, keyboard focus, and intentional responsive behavior.

### Charts support decisions

Charts exist to answer a question. No decorative dashboards. Palette stays muted and token-driven.

### Overlays

Dialogs, sheets, and the command palette should be **lazy-loaded** from the app shell to keep the critical path light.

---

## 11. Layout system

### App shell (locked)

- **Left sidebar** + **top bar** + main content
- Sidebar reflects product hierarchy: Projects → Suites → Cases → Runs
- **Right inspector** is an **opt-in layout primitive**, not permanent chrome (e.g. Run Details, Artifact Viewer)

### Layout primitives

Reusable spacing/structure helpers live in `@agent-eval/ui` (`Stack`, `Cluster`, `Container`, `Panel`, split/inspector slot). Product navigation chrome lives in `apps/web`.

### Responsiveness

Desktop first, tablet second, mobile third. Collapsing the sidebar to an overlay is intentional; do not simply stack every panel vertically without design.

---

## 12. Keyboard-first UX

Treat keyboard as a first-class feature:

- Command palette: **⌘K / Ctrl+K**
- Visible **focus-visible** rings on all interactive elements
- Logical tab order; no focus traps without escape
- Shortcuts documented in the palette and design gallery
- Never remove focus styles for aesthetics

---

## 13. Accessibility

WCAG **AA** is a requirement, not a backlog item.

- Semantic HTML via components
- Sufficient contrast (including semantic badges on both themes)
- Screen reader labels for icon-only controls
- Keyboard parity for pointer interactions
- Reduced motion support

---

## 14. Performance

- Prefer **React Server Components** in `apps/web` by default
- Push `"use client"` to the smallest leaf that needs browser APIs or state
- Lazy-load heavy UI: command palette, dialogs, large chart libraries
- Avoid animation that runs continuously or on every scroll tick
- Measure before adding client-side complexity

---

## 15. Interaction principles

- Feedback is immediate and quiet (subtle hover, clear pressed, honest loading)
- Destructive actions require confirmation
- Empty states explain the next action, not a joke illustration
- Errors are actionable and specific
- Toasts are for confirmations and transient outcomes — not primary error UI

---

## 16. Anti-patterns

Never ship:

- Glassmorphism everywhere
- Giant gradients or neon AI palettes
- Floating card grids as default layout
- Oversized corner radii
- Giant hero sections inside the product
- Unnecessary illustrations
- Giant empty whitespace as "premium"
- Heavy multi-layer shadows
- Decorative charts
- Raw Lucide imports in product code
- Raw `<h1>` / `<p>` styling in product code
- Arbitrary spacing and type sizes
- Domain components inside `packages/ui`
- Springy toy motion with no spatial meaning

---

## 17. Quality checklist (PR)

Before merging UI:

- [ ] Uses tokens / semantic typography / `<Icon />`
- [ ] Works in light and dark
- [ ] Keyboard operable with visible focus
- [ ] Loading / disabled / empty considered
- [ ] Responsive behavior intentional
- [ ] Storybook story for new `packages/ui` components
- [ ] No domain leakage into `packages/ui`
- [ ] Motion justified or absent
- [ ] `pnpm verify` passes

---

## Changelog

| Date       | Change                                                                                                                     |
| ---------- | -------------------------------------------------------------------------------------------------------------------------- |
| 2026-08-02 | Initial principles accepted with Phase 15A design system foundation                                                        |
| 2026-08-02 | Phase 15B: product layouts, DataGrid, UX patterns, navigation shell — see layouts / patterns / navigation / data-grid docs |
