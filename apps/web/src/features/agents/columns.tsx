"use client";

import { Badge, Text } from "@agent-eval/ui";
import { createColumnHelper } from "@tanstack/react-table";

import { entityStatusBadge, entityStatusLabel, formatAgentDate } from "./utils";

import type { Agent } from "@/lib/api/agents";

const columnHelper = createColumnHelper<Agent>();

export const agentColumns = [
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
      const agent = info.row.original;
      const active = agent.versions.find((version) => version.id === agent.active_version_id);
      return (
        <Text as="span" variant="caption" className="tabular-nums">
          {active ? `v${String(active.version_number)}` : "—"}
        </Text>
      );
    },
  }),
  columnHelper.accessor("adapter_id", {
    id: "adapter",
    header: "Adapter",
    enableSorting: false,
    cell: (info) => (
      <Text as="span" variant="caption">
        {info.getValue() ? "Connected" : "None"}
      </Text>
    ),
  }),
  columnHelper.accessor("created_at", {
    header: "Created",
    cell: (info) => (
      <Text as="span" variant="caption" className="tabular-nums">
        {formatAgentDate(info.getValue())}
      </Text>
    ),
  }),
];
