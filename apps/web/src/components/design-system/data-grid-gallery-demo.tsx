"use client";

import {
  Badge,
  DataGrid,
  DataGridColumnVisibility,
  DataGridPagination,
  DataGridSearch,
  IconButton,
  MoreHorizontal,
} from "@agent-eval/ui";
import { useMemo, useState } from "react";

import type {
  ColumnDef,
  PaginationState,
  SortingState,
  VisibilityState,
} from "@tanstack/react-table";

interface SampleRow {
  id: string;
  name: string;
  status: "ready" | "blocked";
  score: number;
}

const rows: SampleRow[] = [
  { id: "a", name: "Sample alpha", status: "ready", score: 98 },
  { id: "b", name: "Sample beta", status: "blocked", score: 41 },
  { id: "c", name: "Sample gamma", status: "ready", score: 87 },
  { id: "d", name: "Sample delta", status: "ready", score: 76 },
  { id: "e", name: "Sample epsilon", status: "blocked", score: 12 },
];

export function DataGridGalleryDemo() {
  const columns = useMemo<ColumnDef<SampleRow>[]>(
    () => [
      { accessorKey: "name", header: "Name" },
      {
        accessorKey: "status",
        header: "Status",
        cell: ({ row }) => (
          <Badge status={row.original.status === "ready" ? "completed" : "warning"}>
            {row.original.status}
          </Badge>
        ),
      },
      {
        accessorKey: "score",
        header: "Score",
        cell: ({ row }) => (
          <span className="font-mono text-[length:var(--ef-text-code)]">{row.original.score}</span>
        ),
      },
    ],
    [],
  );

  const [sorting, setSorting] = useState<SortingState>([]);
  const [globalFilter, setGlobalFilter] = useState("");
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({});
  const [pagination, setPagination] = useState<PaginationState>({ pageIndex: 0, pageSize: 3 });

  const pageCount = Math.max(1, Math.ceil(rows.length / pagination.pageSize));

  return (
    <DataGrid
      columns={columns}
      data={rows}
      getRowId={(row) => row.id}
      sorting={sorting}
      onSortingChange={setSorting}
      globalFilter={globalFilter}
      onGlobalFilterChange={setGlobalFilter}
      columnVisibility={columnVisibility}
      onColumnVisibilityChange={setColumnVisibility}
      pagination={pagination}
      onPaginationChange={setPagination}
      emptyTitle="No samples"
      toolbar={
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <DataGridSearch value={globalFilter} onValueChange={setGlobalFilter} />
          <DataGridColumnVisibility
            columns={[
              { id: "name", label: "Name" },
              { id: "status", label: "Status" },
              { id: "score", label: "Score" },
            ]}
            visibility={columnVisibility}
            onVisibilityChange={setColumnVisibility}
          />
        </div>
      }
      footer={
        <DataGridPagination
          pagination={pagination}
          onPaginationChange={setPagination}
          pageCount={pageCount}
          totalRows={rows.length}
        />
      }
      renderRowActions={() => <IconButton icon={MoreHorizontal} label="Row actions" size="sm" />}
    />
  );
}
