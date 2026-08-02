"use client";

import { Badge, Text } from "@agent-eval/ui";
import Link from "next/link";

import { formatDashboardDate, runStatusBadge, runStatusLabel, truncateId } from "./utils";

import type { Run } from "@/lib/api/runs";

export function RunActivity({
  runs,
  projectNameById,
}: {
  runs: Run[];
  projectNameById: Record<string, string>;
}) {
  if (runs.length === 0) {
    return <Text variant="secondary">No run activity yet.</Text>;
  }

  return (
    <ol className="divide-y divide-border border-y border-border">
      {runs.map((run) => {
        const projectName =
          projectNameById[run.pins.project_id] ?? truncateId(run.pins.project_id, 10);
        return (
          <li key={run.id}>
            <Link
              href={`/runs/${run.id}`}
              className="flex flex-wrap items-center gap-x-3 gap-y-1 py-2.5 transition-colors hover:bg-muted/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <Badge status={runStatusBadge(run.status)}>{runStatusLabel(run.status)}</Badge>
              <Text
                as="span"
                variant="body"
                className="font-mono text-[length:var(--ef-text-caption)]"
              >
                {truncateId(run.id, 12)}
              </Text>
              <Text as="span" variant="caption" className="min-w-0 truncate">
                {projectName}
              </Text>
              <Text as="span" variant="caption" className="ml-auto tabular-nums">
                {formatDashboardDate(run.created_at)}
              </Text>
            </Link>
          </li>
        );
      })}
    </ol>
  );
}
