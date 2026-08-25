"use client";

import { Button, Cluster, Text, toast } from "@agent-eval/ui";
import Link from "next/link";
import { useEffect, useState } from "react";

import {
  canCancelRun,
  elapsedMsSince,
  formatDurationMs,
  formatRunDate,
  formatScoreValue,
  isLiveRunStatus,
  recentActivityLabel,
  runFinishedAt,
  runPassSignal,
  runStartedAt,
  truncateId,
} from "./utils";

import type { RunLiveConnectionState } from "./hooks/use-run-polling";
import type { ExecutionEvent, Run } from "@/lib/api/runs";

import { StatusBadge } from "@/components/status/status-badge";

export interface ExecutionHeaderProps {
  run: Run;
  events: ExecutionEvent[];
  projectName?: string;
  caseLabel?: string;
  agentLabel?: string;
  connection?: RunLiveConnectionState;
  onCancel?: () => void;
  onCopyId?: () => void;
}

function connectionLabelFor(state: RunLiveConnectionState | undefined): string {
  switch (state) {
    case "live":
      return "Live · stream";
    case "connecting":
      return "Live · connecting";
    case "polling":
      return "Live · polling";
    default:
      return "Live · polling";
  }
}

export function ExecutionHeader({
  run,
  events,
  projectName,
  caseLabel,
  agentLabel,
  connection,
  onCancel,
  onCopyId,
}: ExecutionHeaderProps) {
  const live = isLiveRunStatus(run.status);
  const connectionLabel = connectionLabelFor(connection);
  const [nowMs, setNowMs] = useState(() => Date.now());

  useEffect(() => {
    if (!live) return;
    const id = window.setInterval(() => {
      setNowMs(Date.now());
    }, 1000);
    return () => {
      window.clearInterval(id);
    };
  }, [live]);

  const startedAt = runStartedAt(events, run.created_at);
  const finishedAt = runFinishedAt(run.status, events);
  const elapsedMs = live
    ? elapsedMsSince(startedAt, nowMs)
    : finishedAt
      ? new Date(finishedAt).getTime() - new Date(startedAt).getTime()
      : elapsedMsSince(startedAt, nowMs);
  const recent = recentActivityLabel(events);
  const passed = runPassSignal(run);
  const primaryScore = run.scores[0];

  return (
    <div className="overflow-hidden border-b border-border pb-1">
      <div className="flex flex-wrap items-start justify-between gap-4 py-1">
        <div className="space-y-3">
          <Cluster gap={2} className="items-center">
            <StatusBadge status={run.status} passed={passed} />
            {live ? (
              <Text
                as="span"
                variant="caption"
                className="rounded-[var(--ef-radius-control)] bg-running-muted px-2 py-0.5 font-mono uppercase tracking-[0.1em] text-running"
              >
                {connectionLabel}
              </Text>
            ) : null}
            {run.is_partially_graded ? (
              <Text
                as="span"
                variant="caption"
                className="rounded-[var(--ef-radius-control)] bg-warning-muted px-2 py-0.5 text-warning"
              >
                Partially graded
              </Text>
            ) : null}
          </Cluster>
          <div>
            <Text as="div" variant="caption" className="font-mono uppercase tracking-[0.12em]">
              Run
            </Text>
            <Text as="div" variant="body" className="mt-1 font-mono tabular-nums">
              {truncateId(run.id, 28)}
            </Text>
          </div>
        </div>

        <div className="flex flex-col items-end gap-3">
          {primaryScore ? (
            <div className="text-right">
              <Text as="div" variant="caption" className="font-mono uppercase tracking-[0.12em]">
                Score
              </Text>
              <Text
                as="div"
                variant="body"
                className="mt-1 text-[length:var(--ef-text-display)] font-semibold tabular-nums leading-none tracking-tight"
              >
                {formatScoreValue(primaryScore.value)}
              </Text>
            </div>
          ) : null}
          <Cluster gap={2}>
            {canCancelRun(run.status) && onCancel ? (
              <Button type="button" variant="danger" size="sm" onClick={onCancel}>
                Cancel
              </Button>
            ) : null}
            {onCopyId ? (
              <Button type="button" variant="outline" size="sm" onClick={onCopyId}>
                Copy ID
              </Button>
            ) : null}
          </Cluster>
        </div>
      </div>

      <dl className="mt-4 grid gap-0 border-y border-border sm:grid-cols-2 lg:grid-cols-4">
        <ChromeStat label="Started" value={formatRunDate(startedAt)} />
        <ChromeStat
          label="Finished"
          value={finishedAt ? formatRunDate(finishedAt) : live ? "In progress" : "—"}
        />
        <ChromeStat
          label="Elapsed"
          value={elapsedMs === null ? "—" : formatDurationMs(elapsedMs)}
        />
        <ChromeStat label="Recent activity" value={recent ?? "Waiting for events"} />
      </dl>

      <div className="grid gap-3 py-3 sm:grid-cols-3">
        <ContextLink
          label="Project"
          value={projectName ?? truncateId(run.pins.project_id, 12)}
          href={`/projects/${run.pins.project_id}`}
        />
        <ContextLink label="Case" value={caseLabel ?? truncateId(run.pins.case_version_id, 12)} />
        <ContextLink
          label="Agent"
          value={agentLabel ?? truncateId(run.pins.agent_version_id, 12)}
        />
      </div>
    </div>
  );
}

function ChromeStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="border-border px-0 py-3 sm:border-r sm:px-4 sm:first:pl-0 sm:last:border-r-0">
      <Text as="div" variant="caption" className="font-mono uppercase tracking-[0.1em]">
        {label}
      </Text>
      <Text as="div" variant="body" className="mt-1 tabular-nums">
        {value}
      </Text>
    </div>
  );
}

function ContextLink({ label, value, href }: { label: string; value: string; href?: string }) {
  return (
    <div className="min-w-0">
      <Text as="div" variant="caption" className="font-mono uppercase tracking-[0.1em]">
        {label}
      </Text>
      {href ? (
        <Link
          href={href}
          className="mt-1 block truncate text-[length:var(--ef-text-body)] text-foreground underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          {value}
        </Link>
      ) : (
        <Text as="div" variant="body" className="mt-1 truncate">
          {value}
        </Text>
      )}
    </div>
  );
}

/** Convenience for copy toast wiring in stories/tests. */
export function copyRunId(runId: string) {
  return navigator.clipboard.writeText(runId).then(
    () => {
      toast.success("Run ID copied");
    },
    () => {
      toast.error("Could not copy run ID");
    },
  );
}
