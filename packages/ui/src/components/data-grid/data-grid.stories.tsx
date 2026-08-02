"use client";

import { useMemo, useState } from "react";

import { Badge } from "../badge/badge";
import { IconButton } from "../button/icon-button";
import { MoreHorizontal } from "../../icon/icons";
import { DataGrid } from "./data-grid";
import { DataGridColumnVisibility } from "./data-grid-column-visibility";
import { DataGridPagination } from "./data-grid-pagination";
import { DataGridSearch } from "./data-grid-search";

import type { Meta, StoryObj } from "@storybook/react";
import type {
  ColumnDef,
  ColumnFiltersState,
  PaginationState,
  RowSelectionState,
  SortingState,
  VisibilityState,
} from "@tanstack/react-table";

interface DemoItem {
  id: string;
  name: string;
  status: "active" | "paused" | "archived";
  owner: string;
  updatedAt: string;
}

const demoData: DemoItem[] = [
  {
    id: "1",
    name: "Alpha workspace",
    status: "active",
    owner: "Ada",
    updatedAt: "2026-08-01",
  },
  {
    id: "2",
    name: "Beta pipeline",
    status: "paused",
    owner: "Lin",
    updatedAt: "2026-07-28",
  },
  {
    id: "3",
    name: "Gamma archive",
    status: "archived",
    owner: "Sam",
    updatedAt: "2026-06-12",
  },
  {
    id: "4",
    name: "Delta checks",
    status: "active",
    owner: "Ada",
    updatedAt: "2026-08-02",
  },
  {
    id: "5",
    name: "Epsilon suite",
    status: "active",
    owner: "Kai",
    updatedAt: "2026-07-30",
  },
  {
    id: "6",
    name: "Zeta batch",
    status: "paused",
    owner: "Lin",
    updatedAt: "2026-07-15",
  },
];

const statusBadge = {
  active: "success",
  paused: "warning",
  archived: "neutral",
} as const;

function createColumns(): ColumnDef<DemoItem, unknown>[] {
  return [
    {
      accessorKey: "name",
      header: "Name",
      cell: ({ row }) => row.original.name,
    },
    {
      accessorKey: "status",
      header: "Status",
      cell: ({ row }) => (
        <Badge status={statusBadge[row.original.status]}>{row.original.status}</Badge>
      ),
      filterFn: "equalsString",
    },
    {
      accessorKey: "owner",
      header: "Owner",
    },
    {
      accessorKey: "updatedAt",
      header: "Updated",
      cell: ({ row }) => (
        <span className="font-mono text-[length:var(--ef-text-code)]">
          {row.original.updatedAt}
        </span>
      ),
    },
  ];
}

function DataGridPlayground({
  loading = false,
  empty = false,
  selectable = false,
  withActions = false,
}: {
  loading?: boolean;
  empty?: boolean;
  selectable?: boolean;
  withActions?: boolean;
}) {
  const columns = useMemo(() => createColumns(), []);
  const [sorting, setSorting] = useState<SortingState>([]);
  const [globalFilter, setGlobalFilter] = useState("");
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({});
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({});
  const [pagination, setPagination] = useState<PaginationState>({ pageIndex: 0, pageSize: 4 });

  const data = empty ? [] : demoData;
  const pageCount = Math.max(1, Math.ceil((empty ? 0 : demoData.length) / pagination.pageSize));

  return (
    <div className="w-[760px] max-w-full">
      <DataGrid
        columns={columns}
        data={data}
        getRowId={(row) => row.id}
        loading={loading}
        emptyTitle="No items match"
        emptyDescription="Adjust search or filters to see results."
        sorting={sorting}
        onSortingChange={setSorting}
        globalFilter={globalFilter}
        onGlobalFilterChange={setGlobalFilter}
        columnFilters={columnFilters}
        onColumnFiltersChange={setColumnFilters}
        columnVisibility={columnVisibility}
        onColumnVisibilityChange={setColumnVisibility}
        pagination={pagination}
        onPaginationChange={setPagination}
        {...(selectable
          ? {
              enableRowSelection: true,
              rowSelection,
              onRowSelectionChange: setRowSelection,
            }
          : {})}
        toolbar={
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <DataGridSearch value={globalFilter} onValueChange={setGlobalFilter} />
            <DataGridColumnVisibility
              columns={[
                { id: "name", label: "Name" },
                { id: "status", label: "Status" },
                { id: "owner", label: "Owner" },
                { id: "updatedAt", label: "Updated" },
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
            pageCount={empty ? 1 : pageCount}
            totalRows={empty ? 0 : demoData.length}
          />
        }
        {...(withActions
          ? {
              renderRowActions: () => (
                <IconButton icon={MoreHorizontal} label="Row actions" size="sm" />
              ),
            }
          : {})}
      />
      {selectable ? (
        <p className="mt-2 font-mono text-[length:var(--ef-text-caption)] text-muted-foreground">
          selected: {JSON.stringify(rowSelection)}
        </p>
      ) : null}
    </div>
  );
}

const meta = {
  title: "Data/DataGrid",
  component: DataGridPlayground,
  parameters: { layout: "padded" },
} satisfies Meta<typeof DataGridPlayground>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const Loading: Story = { args: { loading: true } };
export const Empty: Story = { args: { empty: true } };
export const WithRowActions: Story = { args: { withActions: true } };
export const SelectableApi: Story = { args: { selectable: true, withActions: true } };

export const Filtered: Story = {
  render: () => {
    function FilteredDemo() {
      const columns = useMemo(() => createColumns(), []);
      const [globalFilter, setGlobalFilter] = useState("alpha");
      const [sorting, setSorting] = useState<SortingState>([{ id: "name", desc: false }]);

      return (
        <div className="w-[760px] max-w-full">
          <DataGrid
            columns={columns}
            data={demoData}
            getRowId={(row) => row.id}
            globalFilter={globalFilter}
            onGlobalFilterChange={setGlobalFilter}
            sorting={sorting}
            onSortingChange={setSorting}
            toolbar={<DataGridSearch value={globalFilter} onValueChange={setGlobalFilter} />}
          />
        </div>
      );
    }
    return <FilteredDemo />;
  },
};
