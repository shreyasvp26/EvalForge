"use client";

import {
  Badge,
  Button,
  ChevronDown,
  ChevronRight,
  Cluster,
  Icon,
  ScrollArea,
  Skeleton,
  Text,
  toast,
} from "@agent-eval/ui";
import { useEffect, useMemo, useRef, useState } from "react";

import {
  eventHeadline,
  eventStatusBadge,
  eventSummary,
  formatDurationMs,
  formatRunTime,
  groupEvents,
  isLiveRunStatus,
  sortEventsBySequence,
} from "./utils";

import type { ExecutionEvent, RunStatus } from "@/lib/api/runs";

import { PanelEmpty } from "@/components/patterns/panel-empty";

export interface ExecutionTimelineProps {
  events: ExecutionEvent[];
  status: RunStatus;
  /** ISO timestamp used as t=0 for relative offsets. */
  startedAt?: string;
  isLoading?: boolean;
  errorMessage?: string | null;
  onRetry?: () => void;
}

export function ExecutionTimeline({
  events,
  status,
  startedAt,
  isLoading = false,
  errorMessage = null,
  onRetry,
}: ExecutionTimelineProps) {
  const sorted = sortEventsBySequence(events);
  const groups = groupEvents(sorted);
  const live = isLiveRunStatus(status);
  const latestId = sorted[sorted.length - 1]?.id ?? null;
  const latestRef = useRef<HTMLLIElement | null>(null);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const originMs = useMemo(() => {
    const origin = startedAt ?? sorted[0]?.occurred_at;
    if (!origin) return null;
    const ms = new Date(origin).getTime();
    return Number.isFinite(ms) ? ms : null;
  }, [startedAt, sorted]);

  useEffect(() => {
    if (!live || !latestId) return;
    const prefersReduced =
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    latestRef.current?.scrollIntoView({
      behavior: prefersReduced ? "auto" : "smooth",
      block: "nearest",
    });
  }, [live, latestId, sorted.length]);

  if (isLoading) {
    return (
      <div className="space-y-3" aria-busy aria-label="Loading execution events">
        <Skeleton className="h-3 w-24" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-[92%]" />
        <Skeleton className="h-10 w-[85%]" />
      </div>
    );
  }

  if (errorMessage) {
    return (
      <div className="space-y-3">
        <Text variant="secondary">{errorMessage}</Text>
        {onRetry ? (
          <Button type="button" size="sm" variant="outline" onClick={onRetry}>
            Try again
          </Button>
        ) : null}
      </div>
    );
  }

  if (sorted.length === 0) {
    return (
      <PanelEmpty
        title={live ? "Waiting for execution events" : "No events recorded"}
        description={
          live
            ? "The timeline will stream tool calls, shell commands, and messages as they happen."
            : "This run finished without recorded execution events."
        }
      />
    );
  }

  return (
    <div className="space-y-4">
      {live && latestId ? (
        <div className="sticky top-0 z-10 -mx-1 border-b border-border bg-background/95 px-1 py-2 backdrop-blur-sm">
          <Cluster gap={2} className="items-center">
            <Badge status="running">Current</Badge>
            <Text variant="caption" className="truncate">
              {(() => {
                const latest = sorted[sorted.length - 1];
                if (!latest) return "—";
                return `${eventHeadline(latest)} · #${String(latest.sequence)}`;
              })()}
            </Text>
          </Cluster>
        </div>
      ) : null}

      <ScrollArea className="h-[min(32rem,70vh)] pr-3">
        <div className="space-y-6">
          {groups.map((group) => (
            <section key={group.id} className="space-y-3">
              <Text
                as="div"
                variant="caption"
                className="font-mono uppercase tracking-[0.12em] text-muted-foreground"
              >
                {group.label}
              </Text>
              <ol className="relative space-y-0 border-l border-border pl-6">
                {group.events.map((event) => {
                  const isLatest = event.id === latestId;
                  const isOpen = expanded[event.id] ?? isLatest;
                  const summary = eventSummary(event);
                  const hasDetails =
                    Object.keys(event.action).length > 0 ||
                    event.artifact_ids.length > 0 ||
                    Object.keys(event.metadata).length > 0;
                  const offsetLabel =
                    originMs === null
                      ? formatRunTime(event.occurred_at)
                      : `+${formatDurationMs(Math.max(0, new Date(event.occurred_at).getTime() - originMs))}`;

                  return (
                    <li
                      key={event.id}
                      ref={isLatest ? latestRef : undefined}
                      className="relative pb-5 last:pb-0"
                    >
                      <span
                        className={
                          isLatest && live
                            ? "absolute -left-[1.625rem] top-1.5 h-2.5 w-2.5 animate-pulse rounded-full border border-running bg-running motion-reduce:animate-none"
                            : "absolute -left-[1.625rem] top-1.5 h-2.5 w-2.5 rounded-full border border-border bg-background"
                        }
                        aria-hidden
                      />
                      <button
                        type="button"
                        className="flex w-full items-start gap-2 rounded-[var(--ef-radius-control)] text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                        aria-expanded={isOpen}
                        onClick={() => {
                          setExpanded((current) => ({
                            ...current,
                            [event.id]: !isOpen,
                          }));
                        }}
                      >
                        <Icon
                          icon={isOpen ? ChevronDown : ChevronRight}
                          size="sm"
                          className="mt-0.5 shrink-0 text-muted-foreground"
                          aria-hidden
                        />
                        <div className="min-w-0 flex-1 space-y-1">
                          <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                            <Text
                              as="span"
                              variant="caption"
                              className="w-16 shrink-0 font-mono tabular-nums text-muted-foreground"
                            >
                              {offsetLabel}
                            </Text>
                            <Badge status={eventStatusBadge(event.kind)}>{event.kind}</Badge>
                            <Text as="span" variant="body" className="font-medium">
                              {eventHeadline(event)}
                            </Text>
                            <Text as="span" variant="caption" className="tabular-nums">
                              #{String(event.sequence)}
                            </Text>
                            <Text
                              as="span"
                              variant="caption"
                              className="tabular-nums text-muted-foreground"
                            >
                              {formatRunTime(event.occurred_at)}
                            </Text>
                          </div>
                          {summary && !isOpen ? (
                            <Text
                              variant="secondary"
                              className="line-clamp-2 font-mono text-[length:var(--ef-text-caption)]"
                            >
                              {summary}
                            </Text>
                          ) : null}
                        </div>
                      </button>

                      {isOpen && hasDetails ? (
                        <div className="mt-2 ml-6 space-y-2 border-l border-border/60 pl-3">
                          {summary ? (
                            <pre className="max-h-48 overflow-auto rounded-[var(--ef-radius-control)] border border-border bg-muted/40 p-3 font-mono text-[length:var(--ef-text-caption)] whitespace-pre-wrap break-words">
                              {summary}
                            </pre>
                          ) : null}
                          {Object.keys(event.action).length > 0 ? (
                            <div className="space-y-1">
                              <Cluster gap={2} className="items-center justify-between">
                                <Text variant="caption">Action payload</Text>
                                <Button
                                  type="button"
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => {
                                    void navigator.clipboard
                                      .writeText(JSON.stringify(event.action, null, 2))
                                      .then(
                                        () => {
                                          toast.success("Action copied");
                                        },
                                        () => {
                                          toast.error("Could not copy");
                                        },
                                      );
                                  }}
                                >
                                  Copy
                                </Button>
                              </Cluster>
                              <pre className="max-h-56 overflow-auto rounded-[var(--ef-radius-control)] border border-border bg-muted/40 p-3 font-mono text-[length:var(--ef-text-caption)] whitespace-pre-wrap break-words">
                                {JSON.stringify(event.action, null, 2)}
                              </pre>
                            </div>
                          ) : null}
                          {event.artifact_ids.length > 0 ? (
                            <Text variant="caption">
                              Artifacts: {event.artifact_ids.join(", ")}
                            </Text>
                          ) : null}
                        </div>
                      ) : null}
                    </li>
                  );
                })}
              </ol>
            </section>
          ))}
        </div>
      </ScrollArea>
    </div>
  );
}
