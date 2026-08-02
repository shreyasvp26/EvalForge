"use client";

import { Badge, Text } from "@agent-eval/ui";
import { createColumnHelper } from "@tanstack/react-table";

import { formatSuiteDate, suiteStatusBadge, suiteStatusLabel } from "./utils";

import type { Suite } from "@/lib/api/suites";

const columnHelper = createColumnHelper<Suite>();

export const suiteColumns = [
  columnHelper.accessor("name", {
    header: "Name",
    cell: (info) => (
      <Text as="span" variant="body" className="font-medium text-foreground">
        {info.getValue()}
      </Text>
    ),
  }),
  columnHelper.accessor("description", {
    header: "Description",
    enableSorting: false,
    cell: (info) => {
      const value = info.getValue();
      return (
        <Text as="span" variant="secondary" className="line-clamp-1 max-w-md">
          {value.trim() ? value : "—"}
        </Text>
      );
    },
  }),
  columnHelper.accessor("status", {
    header: "Status",
    cell: (info) => (
      <Badge status={suiteStatusBadge(info.getValue())}>{suiteStatusLabel(info.getValue())}</Badge>
    ),
  }),
  columnHelper.accessor("active_version_id", {
    id: "active_version",
    header: "Active version",
    enableSorting: false,
    cell: (info) => {
      const suite = info.row.original;
      const active = suite.versions.find((version) => version.id === suite.active_version_id);
      return (
        <Text as="span" variant="caption" className="tabular-nums">
          {active ? `v${String(active.version_number)}` : "—"}
        </Text>
      );
    },
  }),
  columnHelper.accessor("created_at", {
    header: "Created",
    cell: (info) => (
      <Text as="span" variant="caption" className="tabular-nums">
        {formatSuiteDate(info.getValue())}
      </Text>
    ),
  }),
];
