# Layout system

Product pages compose these layouts. Do not invent one-off page chrome.

Import product layouts from `@/components/layouts`. Generic primitives (`Stack`, `InspectorLayout`) come from `@agent-eval/ui`.

---

## AppShell (`apps/web`)

**What:** Sidebar + top bar + main content; hosts command palette, mobile drawer, shortcuts dialog.

**When:** Every authenticated product route (via `(shell)` layout).

**Not:** Business content — pages render _inside_ `main`.

---

## PageLayout

**What:** Width-constrained page canvas (`sm` | `md` | `lg` | `xl` | `full`) with standard padding. `flush` for panes inside SplitView.

**When:** Default wrapper for list and simple pages. Use `width="full"` (`max-w-7xl`, Overview reference) for Overview and DataGrid list pages. Use `lg` for Settings and other readable form columns.

---

## PageHeader

**What:** Eyebrow, title (`Heading` page), description, actions cluster, optional breadcrumbs slot.

**When:** Top of almost every product page. Pass `<Breadcrumbs />` into `breadcrumbs` when the trail belongs with the title (TopBar also shows an auto trail).

---

## Section

**What:** One-purpose block with optional section title, description, and actions.

**When:** Group content under a PageHeader (empty states, grids, forms).

---

## Toolbar

**What:** Dense start/end action row (view switchers vs primary actions).

**When:** Above collections or editors — pair with FilterBar when filtering.

---

## FilterBar

**What:** Search + filter controls + meta (counts), `role="search"`.

**When:** Collection views. Put `DataGridSearch` (or `Input`) in `search`.

---

## DetailLayout

**What:** Detail canvas + **opt-in** right inspector (`InspectorLayout` under the hood).

**When:** Run details, artifact viewers, any page that needs persistent metadata without making the inspector global chrome.

---

## SplitView

**What:** Resizable primary/secondary split (list/detail). Secondary hidden below `md` unless you handle mobile separately.

**When:** Master–detail workflows.

---

## InspectorLayout (`@agent-eval/ui`)

**What:** Generic main + resizable inspector primitive (keyboard-resizable separator).

**When:** Building custom detail chrome; prefer `DetailLayout` in product code.

---

## EmptyContent / LoadingContent / ErrorContent

**What:** Page-level empty, loading, and error regions composing ui Empty/Error states.

**When:** Route bodies that are entirely empty/loading/failed. Prefer skeletons (`PageSkeleton`, `TableSkeleton`) over spinner `LoadingContent` for structured pages — see [product-patterns.md](./product-patterns.md).
