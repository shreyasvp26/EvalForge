# Navigation

The shell should feel closer to Linear / GitHub / Raycast than a generic admin template: calm, dense, keyboard-first.

Implementation: `apps/web/src/components/shell/`.

---

## Sidebar

- Sections: **Workspace** (Projects, Suites, Cases, Runs, Agents) and **System** (Design system).
- Active item: muted background + inset accent bar + `aria-current="page"`.
- Collapsible to icon rail (`lg+`); state persisted in `localStorage` (`evalforge.sidebar.collapsed`).
- Section expand/collapse persisted (`evalforge.sidebar.sections`).
- Chord hints (e.g. `G P`) appear on hover at wide widths.

### Responsive

| Breakpoint | Behavior                                                                 |
| ---------- | ------------------------------------------------------------------------ |
| `lg+`      | Persistent sidebar (collapsible)                                         |
| `< lg`     | Overlay drawer (`MobileNavDrawer`) with Radix focus trap + focus restore |

---

## Top bar

- Auto breadcrumbs from the current path (`breadcrumbsForPath`).
- ⌘K affordance, `?` shortcuts, theme toggle, account menu (sign out).
- Menu opens the mobile drawer below `lg`.

---

## Breadcrumbs

`Breadcrumbs` from `@/components/shell/breadcrumbs`.

- Use in TopBar (automatic) and/or `PageHeader.breadcrumbs`.
- Last crumb is plain text with `aria-current="page"`.

---

## Recent pages

Client-only (`evalforge.nav.recent`). Visits to known nav routes are recorded and shown in the command palette **Recent** group.

---

## Command palette (⌘K / Ctrl+K)

Lazy-loaded client island.

Groups:

1. **Recent** — recent pages
2. **Navigate** — fuzzy match over labels, hrefs, keywords
3. **Projects** — Open Projects, Create Project
4. **Suites** — Open Suites, Create Suite (project-aware when already in a project)
5. **Cases** — Open Cases, Create Case (project-aware when already in a project)
6. **Agents** — Open Agents, Create Agent
7. **Appearance** — Light / Dark / System
8. **Account** — Sign out
9. **Help** — open keyboard shortcuts

Escape closes. Fuzzy matching is client-side (`shouldFilter={false}` + custom score).

---

## Authentication

- Guest routes: `/login` (outside `(shell)`).
- Product routes under `(shell)` are gated by `RequireAuth` + Next.js middleware (session cookie presence).
- JWT access token persists in `localStorage`; session presence cookie `evalforge.auth` enables middleware redirects.
- Top-bar **UserMenu** and command palette **Sign out** clear the session.

## Projects

- Canonical list route: `/projects` (`/` redirects here).
- Detail: `/projects/[projectId]`; settings: `/projects/[projectId]/settings`.
- Sidebar Projects item stays active for nested project routes.
- Command palette: **Open Projects**, **Create Project** (`/projects?create=1`).

## Suites

- Project-scoped list: `/projects/[projectId]/suites`; detail: `/projects/[projectId]/suites/[suiteId]`.
- Global `/suites` is a project picker (suites require a project).
- Version statuses in UI: Draft, Active (published), Superseded, Retired.
- Command palette: **Open Suites**, **Create Suite** (uses current project when present).

## Cases

- Project-scoped list: `/projects/[projectId]/cases`; detail: `/projects/[projectId]/cases/[caseId]`.
- Global `/cases` is a project picker (cases require a project).
- Prompt and case versions: Draft → Active (publish) → Superseded (no retire endpoint for cases).
- Authoring order: create case → prompt draft → case draft (pins a prompt) → publish.
- Command palette: **Open Cases**, **Create Case** (uses current project when present).

## Agents

- Platform-scoped list: `/agents`; detail: `/agents/[agentId]`.
- Adapter detail (1:1 with agent): `/agents/[agentId]/adapters/[adapterId]`.
- Agent versions use `label` + `release_notes`; adapter versions use `label` + `notes`.
- Chord shortcut: `G` then `A`.
- Command palette: **Open Agents**, **Create Agent** (`/agents?create=1`).

## Keyboard shortcuts

Ignored while focus is in inputs / contenteditable.

| Shortcut        | Action                           |
| --------------- | -------------------------------- |
| `⌘K` / `Ctrl+K` | Toggle command palette           |
| `G` then `P`    | Projects                         |
| `G` then `R`    | Runs                             |
| `G` then `A`    | Agents                           |
| `?`             | Shortcuts cheatsheet dialog      |
| `Esc`           | Close palette, drawer, shortcuts |

Cheatsheet: `KeyboardShortcutsDialog`.

---

## Accessibility

- Landmarks: application sidebar `aria-label`, `main#main-content`, breadcrumb `nav`.
- Drawers/dialogs trap focus and restore to the trigger.
- Icon-only controls have `aria-label` via `IconButton`.

---

## Gallery / Storybook

- `/design-system#navigation` and `#keyboard`
- Storybook: **Product Patterns / Navigation** (Breadcrumbs)
