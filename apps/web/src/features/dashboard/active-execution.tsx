"use client";

import { AlertTriangle, Play, Text } from "@agent-eval/ui";
import Link from "next/link";

import { formatRelativeTime, primaryScoreLabel, runPassSignal, truncateId } from "./utils";

import type { Run } from "@/lib/api/runs";

import { PanelEmpty } from "@/components/patterns/panel-empty";
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
      <PanelEmpty
        icon={Play}
        title="No active executions"
        description="Queued, running, and grading evaluations appear here while they execute."
        actionHref="/runs/new"
        actionLabel="Launch run"
      />
    );
  }

  return (
    <ul className="divide-y divide-border overflow-hidden rounded-[var(--ef-radius-panel)] border border-border bg-card shadow-ef-sm">
      {runs.map((run) => {
        const projectName =
          projectNameById[run.pins.project_id] ?? truncateId(run.pins.project_id, 10);
        return (
          <li key={run.id}>
            <Link
              href={`/runs/${run.id}`}
              className="block px-4 py-3.5 transition-colors hover:bg-[var(--ef-accent-muted)]/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 space-y-1.5">
                  <div className="flex flex-wrap items-center gap-2">
                    <StatusBadge status={run.status} size="sm" />
                    <Text as="span" variant="caption" className="font-mono text-foreground">
                      {truncateId(run.id, 12)}
                    </Text>
                  </div>
                  <Text as="p" variant="caption" className="truncate text-muted-foreground">
                    {projectName}
                  </Text>
                </div>
                <Text
                  as="span"
                  variant="caption"
                  className="shrink-0 tabular-nums text-muted-foreground"
                >
                  {formatRelativeTime(run.created_at)}
                </Text>
              </div>
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
    return (
      <PanelEmpty
        icon={AlertTriangle}
        title="No recent failures"
        description="Failed runs and failing scores in the sampled window will show up here."
        actionHref="/runs"
        actionLabel="Browse runs"
      />
    );
  }

  return (
    <ul className="divide-y divide-border overflow-hidden rounded-[var(--ef-radius-panel)] border border-border bg-card shadow-ef-sm">
      {runs.map((run) => {
        const projectName =
          projectNameById[run.pins.project_id] ?? truncateId(run.pins.project_id, 10);
        const score = primaryScoreLabel(run);
        const reason = run.failure_reason?.trim() ?? null;
        return (
          <li key={run.id}>
            <Link
              href={`/runs/${run.id}`}
              className="block px-4 py-3.5 transition-colors hover:bg-danger-muted/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 space-y-1.5">
                  <div className="flex flex-wrap items-center gap-2">
                    <StatusBadge status={run.status} passed={runPassSignal(run)} size="sm" />
                    <Text as="span" variant="caption" className="font-mono text-foreground">
                      {truncateId(run.id, 12)}
                    </Text>
                  </div>
                  <Text as="p" variant="caption" className="truncate text-muted-foreground">
                    {projectName}
                    {score ? ` · ${score}` : ""}
                  </Text>
                  {reason ? (
                    <Text as="p" variant="caption" className="line-clamp-2 text-danger">
                      {reason}
                    </Text>
                  ) : null}
                </div>
                <Text
                  as="span"
                  variant="caption"
                  className="shrink-0 tabular-nums text-muted-foreground"
                >
                  {formatRelativeTime(run.created_at)}
                </Text>
              </div>
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
