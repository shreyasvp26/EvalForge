"use client";

import { Play, Text, cn } from "@agent-eval/ui";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { formatRelativeTime, primaryScoreLabel, runPassSignal, truncateId } from "./utils";

import type { Run } from "@/lib/api/runs";

import { PanelEmpty } from "@/components/patterns/panel-empty";
import { StatusBadge } from "@/components/status/status-badge";

function scoreTone(passed: boolean | null): string {
  if (passed === true) return "text-success";
  if (passed === false) return "text-danger";
  return "text-muted-foreground";
}

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
        actionLabel="Launch run"
      />
    );
  }

  return (
    <div className="overflow-hidden rounded-[var(--ef-radius-panel)] border border-border bg-card shadow-ef-sm">
      <div className="max-h-[20.5rem] overflow-auto">
        <table className="w-full min-w-[36rem] border-collapse text-left">
          <thead className="sticky top-0 z-10 border-b border-border bg-card/95 backdrop-blur-sm">
            <tr>
              {["Status", "Run", "Project", "Score", "Started"].map((heading) => (
                <th
                  key={heading}
                  className="bg-muted/40 px-3 py-2 font-mono text-[length:var(--ef-text-caption)] font-medium uppercase tracking-[0.1em] text-muted-foreground"
                >
                  {heading}
                </th>
              ))}
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
                  className="group cursor-pointer border-b border-border/70 last:border-b-0 transition-colors hover:bg-muted/40"
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
                  <td className="px-3 py-2">
                    <StatusBadge status={run.status} passed={passed} size="sm" />
                  </td>
                  <td className="px-3 py-2">
                    <span className="font-mono text-[length:var(--ef-text-caption)] text-foreground group-hover:text-[var(--ef-accent)]">
                      {truncateId(run.id, 14)}
                    </span>
                  </td>
                  <td className="max-w-[11rem] truncate px-3 py-2">
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
                  <td className="px-3 py-2">
                    <span
                      className={cn(
                        "font-mono text-[length:var(--ef-text-caption)] font-medium tabular-nums",
                        scoreTone(passed),
                      )}
                    >
                      {score ?? "—"}
                    </span>
                    {passed === true ? (
                      <Text as="span" variant="caption" className="ml-1.5 text-success">
                        PASS
                      </Text>
                    ) : null}
                    {passed === false ? (
                      <Text as="span" variant="caption" className="ml-1.5 text-danger">
                        FAIL
                      </Text>
                    ) : null}
                  </td>
                  <td className="px-3 py-2 text-[length:var(--ef-text-caption)] tabular-nums text-muted-foreground">
                    {formatRelativeTime(run.created_at)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
