"use client";

import { Badge, Button, Text } from "@agent-eval/ui";
import { createColumnHelper } from "@tanstack/react-table";

import { canCancelRun, formatRunDate, runStatusBadge, runStatusLabel, truncateId } from "./utils";

import type { Run } from "@/lib/api/runs";

const columnHelper = createColumnHelper<Run>();

export function createRunColumns(options: {
  projectName: string;
  resolveCaseLabel: (caseVersionId: string) => string;
  resolveAgentLabel: (agentVersionId: string) => string;
  onCancel: (run: Run) => void;
}) {
  return [
    columnHelper.accessor("status", {
      header: "Status",
      cell: (info) => (
        <Badge status={runStatusBadge(info.getValue())}>{runStatusLabel(info.getValue())}</Badge>
      ),
    }),
    columnHelper.display({
      id: "project",
      header: "Project",
      enableSorting: false,
      cell: () => (
        <Text as="span" variant="body" className="font-medium">
          {options.projectName}
        </Text>
      ),
    }),
    columnHelper.accessor((row) => row.pins.case_version_id, {
      id: "case",
      header: "Case",
      enableSorting: false,
      cell: (info) => (
        <Text as="span" variant="secondary" className="line-clamp-1 max-w-[12rem]">
          {options.resolveCaseLabel(info.getValue())}
        </Text>
      ),
    }),
    columnHelper.accessor((row) => row.pins.agent_version_id, {
      id: "agent",
      header: "Agent",
      enableSorting: false,
      cell: (info) => (
        <Text as="span" variant="secondary" className="line-clamp-1 max-w-[12rem]">
          {options.resolveAgentLabel(info.getValue())}
        </Text>
      ),
    }),
    columnHelper.accessor("created_at", {
      header: "Created",
      cell: (info) => (
        <Text as="span" variant="caption" className="tabular-nums">
          {formatRunDate(info.getValue())}
        </Text>
      ),
    }),
    columnHelper.display({
      id: "duration",
      header: "Duration",
      enableSorting: false,
      cell: () => (
        <Text as="span" variant="caption" className="tabular-nums text-muted-foreground">
          —
        </Text>
      ),
    }),
    columnHelper.display({
      id: "actions",
      header: "Actions",
      enableSorting: false,
      cell: (info) => {
        const run = info.row.original;
        return (
          <div className="flex items-center gap-2">
            <Text as="span" variant="caption" className="font-mono text-muted-foreground">
              {truncateId(run.id, 10)}
            </Text>
            {canCancelRun(run.status) ? (
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={(event) => {
                  event.stopPropagation();
                  options.onCancel(run);
                }}
              >
                Cancel
              </Button>
            ) : null}
          </div>
        );
      },
    }),
  ];
}
