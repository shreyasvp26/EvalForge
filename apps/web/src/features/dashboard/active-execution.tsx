"use client";

import { Text } from "@agent-eval/ui";
import Link from "next/link";

import { formatDashboardDate, runPassSignal, truncateId } from "./utils";

import type { Run } from "@/lib/api/runs";

import { StatusBadge } from "@/components/status/status-badge";

export function ActiveExecution({
  runs,
  projectNameById,
}: {
  runs: Run[];
  projectNameById: Record<string, string>;
}) {
  if (runs.length === 0) {
    return (
      <Text variant="secondary">
        No active executions. Queued, running, and grading runs appear here.
      </Text>
    );
  }

  return (
    <ul className="divide-y divide-border rounded-[var(--ef-radius-panel)] border border-border">
      {runs.map((run) => {
        const projectName =
          projectNameById[run.pins.project_id] ?? truncateId(run.pins.project_id, 10);
        return (
          <li key={run.id}>
            <Link
              href={`/runs/${run.id}`}
              className="flex flex-wrap items-center gap-x-3 gap-y-1 px-3 py-2.5 transition-colors hover:bg-muted/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <StatusBadge status={run.status} size="sm" />
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
    </ul>
  );
}

export function RecentFailures({
  runs,
  projectNameById,
}: {
  runs: Run[];
  projectNameById: Record<string, string>;
}) {
  if (runs.length === 0) {
    return <Text variant="secondary">No recent failures in the sampled window.</Text>;
  }

  return (
    <ul className="divide-y divide-border rounded-[var(--ef-radius-panel)] border border-border">
      {runs.map((run) => {
        const projectName =
          projectNameById[run.pins.project_id] ?? truncateId(run.pins.project_id, 10);
        const reason = run.failure_reason?.trim() ?? null;
        return (
          <li key={run.id}>
            <Link
              href={`/runs/${run.id}`}
              className="block px-3 py-2.5 transition-colors hover:bg-muted/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                <StatusBadge status={run.status} passed={runPassSignal(run)} size="sm" />
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
              </div>
              {reason ? (
                <Text as="p" variant="caption" className="mt-1 line-clamp-2 text-danger">
                  {reason}
                </Text>
              ) : null}
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
