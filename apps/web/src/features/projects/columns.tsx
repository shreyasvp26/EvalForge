"use client";

import { Badge, Text } from "@agent-eval/ui";
import { createColumnHelper } from "@tanstack/react-table";

import { formatProjectDate, projectStatusBadge, projectStatusLabel } from "./utils";

import type { Project } from "@/lib/api/projects";

const columnHelper = createColumnHelper<Project>();

export const projectColumns = [
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
    cell: (info) => {
      const value = info.getValue();
      return (
        <Text as="span" variant="secondary" className="line-clamp-1 max-w-md">
          {value.trim() ? value : "—"}
        </Text>
      );
    },
    enableSorting: false,
  }),
  columnHelper.accessor("status", {
    header: "Status",
    cell: (info) => (
      <Badge status={projectStatusBadge(info.getValue())}>
        {projectStatusLabel(info.getValue())}
      </Badge>
    ),
  }),
  columnHelper.accessor("created_at", {
    header: "Created",
    cell: (info) => (
      <Text as="span" variant="caption" className="tabular-nums">
        {formatProjectDate(info.getValue())}
      </Text>
    ),
  }),
];
