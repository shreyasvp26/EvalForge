# Product UX patterns

Reusable patterns live in `apps/web/src/components/patterns`. They compose `@agent-eval/ui` — they are **not** domain features.

Every empty/error/success state should answer:

1. What happened?
2. Why?
3. What can the user do next?

Avoid “No data found.”

---

## Loading philosophy

Prefer **skeletons that preserve layout** over centered spinners.

| Pattern          | Use                                             |
| ---------------- | ----------------------------------------------- |
| `PageSkeleton`   | Full page (header + body) while a route loads   |
| `TableSkeleton`  | Collection / DataGrid shaped load               |
| `DetailSkeleton` | Detail + optional inspector                     |
| `FormSkeleton`   | Form fields hydrate                             |
| `GlobalLoading`  | Rare full-viewport block (boot) — use sparingly |

`LoadingContent` with `variant="skeleton"` is acceptable for small regions; default spinner is a last resort.

---

## Empty & status states

| Pattern                 | Use                                                    |
| ----------------------- | ------------------------------------------------------ |
| `SearchEmptyState`      | Query returned nothing — mention the query when known  |
| `NoResultsState`        | Filters excluded everything                            |
| `NotFoundState`         | Missing resource / bad URL (`resourceLabel`)           |
| `PermissionDeniedState` | Authorization failure                                  |
| `ComingSoonState`       | Intentionally unfinished surface                       |
| `SuccessState`          | Terminal success in a multi-step flow (not a toast)    |
| `EmptyContent`          | Generic page empty (compose with a specific icon/copy) |

First-time empty (“you have never created X”) should use clear create CTAs via the `action` slot.

---

## Errors

| Pattern                          | Use                                                          |
| -------------------------------- | ------------------------------------------------------------ |
| `InlineError`                    | Field validation (`density="field"`) or compact block errors |
| `ErrorContent` / ui `ErrorState` | Page-level known failure + retry action                      |
| `ErrorBoundary`                  | Unexpected render failures; reset + actionable copy          |

Toasts (ui `toast`) are for transient confirmations — not primary error UI.

---

## ConfirmationDialog

Standard confirm for destructive and non-destructive actions.

Supports:

- `variant="default" | "destructive"`
- Custom icon
- Async `onConfirm` with loading on the primary button
- Focus trap, Escape, blocked dismiss while loading (configurable)

```tsx
<ConfirmationDialog
  open={open}
  onOpenChange={setOpen}
  variant="destructive"
  title="Delete this item?"
  description="This can’t be undone. Related history stays immutable."
  confirmLabel="Delete"
  onConfirm={async () => {
    await doDelete();
  }}
/>
```

---

## Storybook

Stories under **Product Patterns** (loaded from `apps/web` into the ui Storybook). Gallery: `/design-system#patterns`.
