"use client";

import { Badge, Text } from "@agent-eval/ui";
import { createColumnHelper } from "@tanstack/react-table";

import {
  entityStatusBadge,
  entityStatusLabel,
  familyStatusBadge,
  familyStatusLabel,
  formatGraderDate,
} from "./utils";

import type { Grader } from "@/lib/api/graders";

const columnHelper = createColumnHelper<Grader>();

export const graderColumns = [
  columnHelper.accessor("name", {
    header: "Name",
    cell: (info) => (
      <Text as="span" variant="body" className="font-medium text-foreground">
        {info.getValue()}
      </Text>
    ),
  }),
  columnHelper.accessor("family", {
    header: "Family",
    cell: (info) => (
      <Badge status={familyStatusBadge(info.getValue())}>
        {familyStatusLabel(info.getValue())}
      </Badge>
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
      <Badge status={entityStatusBadge(info.getValue())}>
        {entityStatusLabel(info.getValue())}
      </Badge>
    ),
  }),
  columnHelper.accessor("active_version_id", {
    id: "active_version",
    header: "Active version",
    enableSorting: false,
    cell: (info) => {
      const grader = info.row.original;
      const active = grader.versions.find((version) => version.id === grader.active_version_id);
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
        {formatGraderDate(info.getValue())}
      </Text>
    ),
  }),
];
