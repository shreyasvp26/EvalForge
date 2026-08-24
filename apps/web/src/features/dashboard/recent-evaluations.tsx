"use client";

import { Play } from "@agent-eval/ui";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { formatDashboardDate, primaryScoreLabel, runPassSignal, truncateId } from "./utils";

import type { Run } from "@/lib/api/runs";

import { PanelEmpty } from "@/components/patterns/panel-empty";
import { StatusBadge } from "@/components/status/status-badge";

export function RecentEvaluations({
  runs,
  projectNameById,
}: {
  runs: Run[];
  projectNameById: Record<string, string>;
}) {
  const router = useRouter();

  if (runs.length === 0) {
    return (
      <PanelEmpty
        icon={Play}
        title="No evaluations yet"
        description="Create a case, choose an agent and grader, then launch your first evaluation."
        actionHref="/runs/new"
        actionLabel="Create evaluation"
      />
    );
  }

  return (
    <div className="overflow-x-auto rounded-[var(--ef-radius-panel)] border border-border bg-card shadow-ef-sm">
      <table className="w-full min-w-[40rem] border-collapse text-left">
        <thead>
          <tr className="border-b border-border bg-muted/30">
            <th className="px-4 py-2.5 font-mono text-[length:var(--ef-text-caption)] font-medium uppercase tracking-[0.1em] text-muted-foreground">
              Status
            </th>
            <th className="px-4 py-2.5 font-mono text-[length:var(--ef-text-caption)] font-medium uppercase tracking-[0.1em] text-muted-foreground">
              Run
            </th>
            <th className="px-4 py-2.5 font-mono text-[length:var(--ef-text-caption)] font-medium uppercase tracking-[0.1em] text-muted-foreground">
              Project
            </th>
            <th className="px-4 py-2.5 font-mono text-[length:var(--ef-text-caption)] font-medium uppercase tracking-[0.1em] text-muted-foreground">
              Score
            </th>
            <th className="px-4 py-2.5 font-mono text-[length:var(--ef-text-caption)] font-medium uppercase tracking-[0.1em] text-muted-foreground">
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
              <tr
                key={run.id}
                className="group cursor-pointer border-b border-border last:border-b-0 transition-colors hover:bg-muted/40"
                onClick={() => {
                  router.push(`/runs/${run.id}`);
                }}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    router.push(`/runs/${run.id}`);
                  }
                }}
                tabIndex={0}
                role="link"
              >
                <td className="px-4 py-3">
                  <StatusBadge status={run.status} passed={passed} size="sm" />
                </td>
                <td className="px-4 py-3">
                  <span className="font-mono text-[length:var(--ef-text-caption)] text-foreground group-hover:underline group-hover:underline-offset-2">
                    {truncateId(run.id, 14)}
                  </span>
                </td>
                <td className="max-w-[12rem] truncate px-4 py-3">
                  <Link
                    href={`/projects/${run.pins.project_id}`}
                    className="text-[length:var(--ef-text-body)] text-muted-foreground underline-offset-2 hover:text-foreground hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    onClick={(event) => {
                      event.stopPropagation();
                    }}
                  >
                    {projectName}
                  </Link>
                </td>
                <td className="px-4 py-3 font-mono text-[length:var(--ef-text-caption)] tabular-nums">
                  {score ?? "—"}
                </td>
                <td className="px-4 py-3 text-[length:var(--ef-text-caption)] tabular-nums text-muted-foreground">
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
