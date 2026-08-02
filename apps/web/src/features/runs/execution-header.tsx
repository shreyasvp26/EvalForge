"use client";

import { Badge, Button, Cluster, Text } from "@agent-eval/ui";
import { useEffect, useState } from "react";

import {
  canCancelRun,
  elapsedMsSince,
  formatDurationMs,
  formatRunDate,
  isLiveRunStatus,
  recentActivityLabel,
  runFinishedAt,
  runStartedAt,
  runStatusBadge,
  runStatusLabel,
  truncateId,
} from "./utils";

import type { ExecutionEvent, Run } from "@/lib/api/runs";

export interface ExecutionHeaderProps {
  run: Run;
  events: ExecutionEvent[];
  onCancel?: () => void;
  onCopyId?: () => void;
}

export function ExecutionHeader({ run, events, onCancel, onCopyId }: ExecutionHeaderProps) {
  const live = isLiveRunStatus(run.status);
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

  return (
    <div className="space-y-4 rounded-[var(--ef-radius-panel)] border border-border bg-card/40 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-2">
          <Cluster gap={2} className="items-center">
            <Badge status={runStatusBadge(run.status)}>{runStatusLabel(run.status)}</Badge>
            {live ? <Badge status="running">Live</Badge> : null}
            {run.is_partially_graded ? <Badge status="warning">Partially graded</Badge> : null}
          </Cluster>
          <Text as="div" variant="caption" className="font-mono tabular-nums">
            {truncateId(run.id, 24)}
          </Text>
        </div>
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

      <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
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

      <div className="border-t border-border pt-3">
        <Text as="div" variant="caption" className="mb-2">
          Pinned versions
        </Text>
        <div className="flex flex-wrap gap-x-4 gap-y-1">
          <PinChip label="project" value={truncateId(run.pins.project_id, 10)} />
          <PinChip label="case" value={truncateId(run.pins.case_version_id, 10)} />
          <PinChip label="prompt" value={truncateId(run.pins.prompt_version_id, 10)} />
          <PinChip label="agent" value={truncateId(run.pins.agent_version_id, 10)} />
          <PinChip label="adapter" value={truncateId(run.pins.adapter_version_id, 10)} />
          <PinChip label="graders" value={String(run.pins.grader_version_ids.length)} />
        </div>
      </div>
    </div>
  );
}

function ChromeStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="space-y-1">
      <Text as="div" variant="caption">
        {label}
      </Text>
      <Text as="div" variant="body" className="tabular-nums">
        {value}
      </Text>
    </div>
  );
}

function PinChip({ label, value }: { label: string; value: string }) {
  return (
    <Text as="span" variant="caption" className="font-mono">
      <span className="text-muted-foreground">{label}</span> {value}
    </Text>
  );
}
