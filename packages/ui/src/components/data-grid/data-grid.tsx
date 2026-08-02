"use client";

import {
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { useCallback, useMemo, useRef, useState } from "react";

import { Icon } from "../../icon/icon";
import { ArrowDown, ArrowUp, ChevronsUpDown } from "../../icon/icons";
import { cn } from "../../lib/cn";
import { Text } from "../../typography/text";
import { EmptyState } from "../empty-state/empty-state";
import { Skeleton } from "../skeleton/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../table/table";

import type { DataGridProps } from "./types";
import type { ColumnDef, Row } from "@tanstack/react-table";
import type { KeyboardEvent } from "react";

function SortIcon({ sorted }: { sorted: false | "asc" | "desc" }) {
  if (sorted === "asc") return <Icon icon={ArrowUp} size="xs" aria-hidden />;
  if (sorted === "desc") return <Icon icon={ArrowDown} size="xs" aria-hidden />;
  return <Icon icon={ChevronsUpDown} size="xs" className="opacity-40" aria-hidden />;
}

function LoadingRows({ columnCount, rowCount }: { columnCount: number; rowCount: number }) {
  return (
    <>
      {Array.from({ length: rowCount }).map((_, rowIndex) => (
        <TableRow key={`loading-${String(rowIndex)}`} aria-hidden>
          {Array.from({ length: columnCount }).map((_, colIndex) => (
            <TableCell key={`loading-${String(rowIndex)}-${String(colIndex)}`}>
              <Skeleton className="h-4 w-full max-w-[9rem]" />
            </TableCell>
          ))}
        </TableRow>
      ))}
    </>
  );
}

/**
 * Production DataGrid built on TanStack Table + design-system table primitives.
 * Domain-agnostic: pass columns + data only.
 */
export function DataGrid<TData>({
  columns,
  data,
  getRowId,
  loading = false,
  loadingRowCount = 5,
  emptyTitle = "No results",
  emptyDescription,
  emptyAction,
  globalFilter,
  onGlobalFilterChange,
  sorting,
  onSortingChange,
  columnFilters,
  onColumnFiltersChange,
  columnVisibility,
  onColumnVisibilityChange,
  rowSelection,
  onRowSelectionChange,
  enableRowSelection,
  pagination,
  onPaginationChange,
  manualPagination = false,
  manualSorting = false,
  manualFiltering = false,
  pageCount,
  renderRowActions,
  onRowActivate,
  toolbar,
  footer,
  className,
  "aria-label": ariaLabel = "Data grid",
}: DataGridProps<TData>) {
  const [focusedRowIndex, setFocusedRowIndex] = useState(-1);
  const bodyRef = useRef<HTMLTableSectionElement>(null);

  const columnsWithActions = useMemo(() => {
    if (!renderRowActions) return columns;
    const actionsColumn: ColumnDef<TData> = {
      id: "__actions",
      header: () => <span className="sr-only">Actions</span>,
      cell: ({ row }) => (
        <div
          className="flex justify-end"
          onClick={(event) => {
            event.stopPropagation();
          }}
          onKeyDown={(event) => {
            event.stopPropagation();
          }}
        >
          {renderRowActions(row)}
        </div>
      ),
      enableSorting: false,
      enableHiding: false,
      size: 64,
    };
    return [...columns, actionsColumn];
  }, [columns, renderRowActions]);

  const table = useReactTable({
    data,
    columns: columnsWithActions,
    state: {
      ...(sorting !== undefined ? { sorting } : {}),
      ...(columnFilters !== undefined ? { columnFilters } : {}),
      ...(columnVisibility !== undefined ? { columnVisibility } : {}),
      ...(rowSelection !== undefined ? { rowSelection } : {}),
      ...(pagination !== undefined ? { pagination } : {}),
      ...(globalFilter !== undefined ? { globalFilter } : {}),
    },
    ...(getRowId !== undefined ? { getRowId } : {}),
    ...(onSortingChange !== undefined ? { onSortingChange } : {}),
    ...(onColumnFiltersChange !== undefined ? { onColumnFiltersChange } : {}),
    ...(onColumnVisibilityChange !== undefined ? { onColumnVisibilityChange } : {}),
    ...(onRowSelectionChange !== undefined ? { onRowSelectionChange } : {}),
    ...(onPaginationChange !== undefined ? { onPaginationChange } : {}),
    ...(onGlobalFilterChange !== undefined ? { onGlobalFilterChange } : {}),
    ...(enableRowSelection !== undefined ? { enableRowSelection } : {}),
    ...(pageCount !== undefined ? { pageCount } : {}),
    manualPagination,
    manualSorting,
    manualFiltering,
    getCoreRowModel: getCoreRowModel(),
    ...(manualSorting ? {} : { getSortedRowModel: getSortedRowModel() }),
    ...(manualFiltering ? {} : { getFilteredRowModel: getFilteredRowModel() }),
    ...(manualPagination || pagination !== undefined || onPaginationChange !== undefined
      ? { getPaginationRowModel: getPaginationRowModel() }
      : {}),
  });

  const rows = table.getRowModel().rows;
  const visibleColumnCount = table.getVisibleLeafColumns().length;

  const focusRow = useCallback((index: number) => {
    setFocusedRowIndex(index);
    const rowEl = bodyRef.current?.querySelector<HTMLElement>(
      `[data-row-index="${String(index)}"]`,
    );
    rowEl?.focus();
  }, []);

  const onBodyKeyDown = useCallback(
    (event: KeyboardEvent<HTMLTableSectionElement>) => {
      if (rows.length === 0) return;
      if (event.key === "ArrowDown") {
        event.preventDefault();
        focusRow(Math.min(rows.length - 1, Math.max(0, focusedRowIndex) + 1));
      } else if (event.key === "ArrowUp") {
        event.preventDefault();
        focusRow(Math.max(0, (focusedRowIndex < 0 ? 0 : focusedRowIndex) - 1));
      } else if (event.key === "Home") {
        event.preventDefault();
        focusRow(0);
      } else if (event.key === "End") {
        event.preventDefault();
        focusRow(rows.length - 1);
      } else if ((event.key === "Enter" || event.key === " ") && focusedRowIndex >= 0) {
        const row = rows[focusedRowIndex];
        if (row && onRowActivate) {
          event.preventDefault();
          onRowActivate(row);
        }
      }
    },
    [focusRow, focusedRowIndex, onRowActivate, rows],
  );

  const activateRow = useCallback(
    (row: Row<TData>) => {
      onRowActivate?.(row);
    },
    [onRowActivate],
  );

  return (
    <div className={cn("space-y-3", className)}>
      {toolbar}
      <Table
        aria-label={ariaLabel}
        aria-busy={loading || undefined}
        aria-rowcount={loading ? loadingRowCount : rows.length}
      >
        <TableHeader>
          {table.getHeaderGroups().map((headerGroup) => (
            <TableRow key={headerGroup.id}>
              {headerGroup.headers.map((header) => {
                const canSort = header.column.getCanSort();
                const sorted = header.column.getIsSorted();
                return (
                  <TableHead
                    key={header.id}
                    style={
                      header.column.getSize() !== 150 ? { width: header.getSize() } : undefined
                    }
                    {...(sorted === "asc"
                      ? { "aria-sort": "ascending" as const }
                      : sorted === "desc"
                        ? { "aria-sort": "descending" as const }
                        : canSort
                          ? { "aria-sort": "none" as const }
                          : {})}
                  >
                    {header.isPlaceholder ? null : canSort ? (
                      <button
                        type="button"
                        className="inline-flex items-center gap-1.5 rounded-[var(--ef-radius-control)] text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                        onClick={header.column.getToggleSortingHandler()}
                      >
                        {flexRender(header.column.columnDef.header, header.getContext())}
                        <SortIcon sorted={sorted} />
                      </button>
                    ) : (
                      flexRender(header.column.columnDef.header, header.getContext())
                    )}
                  </TableHead>
                );
              })}
            </TableRow>
          ))}
        </TableHeader>
        <TableBody
          ref={bodyRef}
          tabIndex={rows.length > 0 ? 0 : undefined}
          onKeyDown={onBodyKeyDown}
        >
          {loading ? (
            <LoadingRows columnCount={Math.max(visibleColumnCount, 1)} rowCount={loadingRowCount} />
          ) : rows.length === 0 ? (
            <TableRow>
              <TableCell colSpan={Math.max(visibleColumnCount, 1)} className="p-2">
                <EmptyState
                  title={emptyTitle}
                  {...(emptyDescription !== undefined ? { description: emptyDescription } : {})}
                  {...(emptyAction !== undefined ? { action: emptyAction } : {})}
                  className="border-0"
                />
              </TableCell>
            </TableRow>
          ) : (
            rows.map((row, index) => {
              const selected = row.getIsSelected();
              return (
                <TableRow
                  key={row.id}
                  data-row-index={index}
                  data-state={selected ? "selected" : undefined}
                  tabIndex={-1}
                  className={cn(
                    onRowActivate ? "cursor-pointer" : undefined,
                    focusedRowIndex === index ? "bg-muted/60" : undefined,
                  )}
                  onFocus={() => {
                    setFocusedRowIndex(index);
                  }}
                  onClick={() => {
                    if (onRowActivate) activateRow(row);
                  }}
                  onKeyDown={(event) => {
                    if ((event.key === "Enter" || event.key === " ") && onRowActivate) {
                      event.preventDefault();
                      activateRow(row);
                    }
                  }}
                >
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </TableCell>
                  ))}
                </TableRow>
              );
            })
          )}
        </TableBody>
      </Table>
      {footer}
      {!loading && rows.length > 0 ? (
        <Text variant="caption" className="sr-only">
          {String(rows.length)} rows. Use arrow keys to move, Enter to activate.
        </Text>
      ) : null}
    </div>
  );
}

export type { DataGridProps } from "./types";
