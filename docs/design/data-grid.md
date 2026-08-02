# DataGrid

Domain-agnostic data table in `@agent-eval/ui`, built on **TanStack Table** + design-system table primitives.

```tsx
import {
  DataGrid,
  DataGridSearch,
  DataGridColumnVisibility,
  DataGridPagination,
} from "@agent-eval/ui";
import type { ColumnDef } from "@tanstack/react-table";
```

**Never** hardcode Projects, Runs, Agents, or other EvalForge resources inside the grid package.

---

## Architecture

- `DataGrid` owns table rendering, sort headers, loading skeletons, empty state, keyboard row focus, optional row-actions column.
- State is **controlled** for production use: sorting, globalFilter, columnFilters, columnVisibility, pagination, rowSelection.
- Helpers:
  - `DataGridSearch` → `globalFilter`
  - `DataGridColumnVisibility` → `columnVisibility`
  - `DataGridPagination` → `pagination` + `pageCount`

Compose with product `FilterBar` / `Toolbar` / `PageLayout` in `apps/web`.

---

## Supported features

| Feature           | Notes                                                            |
| ----------------- | ---------------------------------------------------------------- |
| Sorting           | Clickable headers; `aria-sort`                                   |
| Global search     | Controlled string + `DataGridSearch`                             |
| Column filtering  | `columnFilters` + column `filterFn`                              |
| Column visibility | Controlled + menu helper                                         |
| Loading           | Skeleton rows (`loading`, `loadingRowCount`)                     |
| Empty             | Title / description / action slots                               |
| Keyboard          | Arrow Up/Down, Home/End, Enter/Space activate                    |
| Row selection     | **API only** — enable + selection column if you need UI          |
| Row actions       | `renderRowActions(row)`                                          |
| Pagination        | Client `getPaginationRowModel` when `pagination` state is passed |

---

## Server-side pagination readiness

Today: pass `pagination` / `onPaginationChange` for client paging.

Later (server):

```tsx
<DataGrid
  manualPagination
  manualSorting
  manualFiltering
  pageCount={serverPageCount}
  pagination={pagination}
  onPaginationChange={setPagination}
  // data = current page from API
/>
```

Keep column defs stable (`useMemo`) to avoid unnecessary re-renders.

---

## Mobile

Wide tables use horizontal scroll (`overflow-x-auto`). Prefer fewer visible columns on small screens via controlled `columnVisibility` (hide low-priority columns below `md`). A card/list alternate layout is deferred until product CRUD.

---

## Extension points

- Custom cells via TanStack `columnDef.cell`
- `getRowId` for stable keys
- `onRowActivate` for navigation
- `toolbar` / `footer` slots
- Selection: `enableRowSelection` + `rowSelection` without forcing checkboxes

---

## Example (controlled)

```tsx
const columns = useMemo<ColumnDef<Item>[]>(() => [/* … */], []);
const [sorting, setSorting] = useState<SortingState>([]);
const [globalFilter, setGlobalFilter] = useState("");
const [pagination, setPagination] = useState({ pageIndex: 0, pageSize: 20 });

<DataGrid
  columns={columns}
  data={items}
  getRowId={(row) => row.id}
  sorting={sorting}
  onSortingChange={setSorting}
  globalFilter={globalFilter}
  onGlobalFilterChange={setGlobalFilter}
  pagination={pagination}
  onPaginationChange={setPagination}
  toolbar={<DataGridSearch value={globalFilter} onValueChange={setGlobalFilter} />}
  footer={
    <DataGridPagination
      pagination={pagination}
      onPaginationChange={setPagination}
      pageCount={Math.ceil(items.length / pagination.pageSize) || 1}
      totalRows={items.length}
    />
  }
/>;
```

---

## Storybook / gallery

- Storybook: **Data / DataGrid** (default, loading, empty, filtered, selectable, row actions)
- Gallery: `/design-system#datagrid`
