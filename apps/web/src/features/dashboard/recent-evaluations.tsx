"use client";

import { Text } from "@agent-eval/ui";
import Link from "next/link";

import { formatDashboardDate, primaryScoreLabel, runPassSignal, truncateId } from "./utils";

import type { Run } from "@/lib/api/runs";

import { StatusBadge } from "@/components/status/status-badge";

export function RecentEvaluations({
  runs,
  projectNameById,
}: {
  runs: Run[];
  projectNameById: Record<string, string>;
}) {
  if (runs.length === 0) {
    return <Text variant="secondary">No evaluations yet. Launch a run to populate this feed.</Text>;
  }

  return (
    <div className="overflow-x-auto rounded-[var(--ef-radius-panel)] border border-border">
      <table className="w-full min-w-[40rem] border-collapse text-left">
        <thead>
          <tr className="border-b border-border bg-muted/40">
            <th className="px-3 py-2 font-mono text-[length:var(--ef-text-caption)] font-medium uppercase tracking-[0.1em] text-muted-foreground">
              Status
            </th>
            <th className="px-3 py-2 font-mono text-[length:var(--ef-text-caption)] font-medium uppercase tracking-[0.1em] text-muted-foreground">
              Run
            </th>
            <th className="px-3 py-2 font-mono text-[length:var(--ef-text-caption)] font-medium uppercase tracking-[0.1em] text-muted-foreground">
              Project
            </th>
            <th className="px-3 py-2 font-mono text-[length:var(--ef-text-caption)] font-medium uppercase tracking-[0.1em] text-muted-foreground">
              Score
            </th>
            <th className="px-3 py-2 font-mono text-[length:var(--ef-text-caption)] font-medium uppercase tracking-[0.1em] text-muted-foreground">
              Created
            </th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => {
            const projectName =
              projectNameById[run.pins.project_id] ?? truncateId(run.pins.project_id, 10);
            const score = primaryScoreLabel(run);
            const passed = runPassSignal(run);
            return (
              <tr key={run.id} className="border-b border-border last:border-b-0">
                <td className="px-3 py-2.5">
                  <StatusBadge status={run.status} passed={passed} size="sm" />
                </td>
                <td className="px-3 py-2.5">
                  <Link
                    href={`/runs/${run.id}`}
                    className="font-mono text-[length:var(--ef-text-caption)] text-foreground underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    {truncateId(run.id, 14)}
                  </Link>
                </td>
                <td className="max-w-[12rem] truncate px-3 py-2.5">
                  <Link
                    href={`/projects/${run.pins.project_id}`}
                    className="text-[length:var(--ef-text-body)] text-muted-foreground underline-offset-2 hover:text-foreground hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    {projectName}
                  </Link>
                </td>
                <td className="px-3 py-2.5 font-mono text-[length:var(--ef-text-caption)] tabular-nums">
                  {score ?? "—"}
                </td>
                <td className="px-3 py-2.5 text-[length:var(--ef-text-caption)] tabular-nums text-muted-foreground">
                  {formatDashboardDate(run.created_at)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
