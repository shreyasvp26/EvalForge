import type {
  ColumnDef,
  ColumnFiltersState,
  OnChangeFn,
  PaginationState,
  Row,
  RowSelectionState,
  SortingState,
  VisibilityState,
} from "@tanstack/react-table";
import type { ReactNode } from "react";

/**
 * Generic DataGrid contract. No domain types — consumers supply TData + columns.
 */
export interface DataGridProps<TData> {
  /**
   * Column defs from `createColumnHelper` — value generics vary per column.
   * `any` matches TanStack Table's recommended consumer typing with exactOptionalPropertyTypes.
   */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any -- TanStack ColumnDef value variance
  columns: ColumnDef<TData, any>[];
  data: TData[];
  getRowId?: (originalRow: TData, index: number) => string;

  loading?: boolean;
  loadingRowCount?: number;

  emptyTitle?: string;
  emptyDescription?: string;
  emptyAction?: ReactNode;

  /** Controlled global filter (search). Pair with DataGridSearch or your own Input. */
  globalFilter?: string;
  onGlobalFilterChange?: OnChangeFn<string>;

  sorting?: SortingState;
  onSortingChange?: OnChangeFn<SortingState>;

  columnFilters?: ColumnFiltersState;
  onColumnFiltersChange?: OnChangeFn<ColumnFiltersState>;

  columnVisibility?: VisibilityState;
  onColumnVisibilityChange?: OnChangeFn<VisibilityState>;

  /** Row selection state only — no forced checkbox UI. Enable + wire selection column yourself if needed. */
  rowSelection?: RowSelectionState;
  onRowSelectionChange?: OnChangeFn<RowSelectionState>;
  enableRowSelection?: boolean | ((row: Row<TData>) => boolean);

  pagination?: PaginationState;
  onPaginationChange?: OnChangeFn<PaginationState>;
  /** When true, data is already a page (server-side). Requires pageCount. */
  manualPagination?: boolean;
  manualSorting?: boolean;
  manualFiltering?: boolean;
  pageCount?: number;

  renderRowActions?: (row: Row<TData>) => ReactNode;
  onRowActivate?: (row: Row<TData>) => void;

  /** Optional toolbar rendered above the grid (search, filters, column menu). */
  toolbar?: ReactNode;
  /** Optional footer (e.g. DataGridPagination). */
  footer?: ReactNode;

  className?: string;
  "aria-label"?: string;
}
