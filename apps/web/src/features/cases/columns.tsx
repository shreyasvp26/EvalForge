"use client";

import { Badge, Text } from "@agent-eval/ui";
import { createColumnHelper } from "@tanstack/react-table";

import { caseStatusBadge, caseStatusLabel, formatCaseDate } from "./utils";

import type { Case } from "@/lib/api/cases";

const columnHelper = createColumnHelper<Case>();

export const caseColumns = [
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
      <Badge status={caseStatusBadge(info.getValue())}>{caseStatusLabel(info.getValue())}</Badge>
    ),
  }),
  columnHelper.accessor("active_version_id", {
    id: "active_version",
    header: "Active case version",
    enableSorting: false,
    cell: (info) => {
      const caseItem = info.row.original;
      const active = caseItem.versions.find((version) => version.id === caseItem.active_version_id);
      return (
        <Text as="span" variant="caption" className="tabular-nums">
          {active ? `v${String(active.version_number)}` : "—"}
        </Text>
      );
    },
  }),
  columnHelper.accessor("active_prompt_version_id", {
    id: "active_prompt",
    header: "Active prompt",
    enableSorting: false,
    cell: (info) => {
      const caseItem = info.row.original;
      const active = caseItem.prompt_versions.find(
        (version) => version.id === caseItem.active_prompt_version_id,
      );
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
        {formatCaseDate(info.getValue())}
      </Text>
    ),
  }),
];
