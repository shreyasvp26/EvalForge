import type { ExecutionEvent, Run, RunStatus } from "@/lib/api/runs";

export function formatRunDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function formatDurationMs(ms: number): string {
  if (!Number.isFinite(ms) || ms < 0) return "—";
  if (ms < 1000) return `${String(Math.round(ms))}ms`;
  const seconds = ms / 1000;
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const minutes = Math.floor(seconds / 60);
  const rem = Math.round(seconds % 60);
  return `${String(minutes)}m ${String(rem)}s`;
}

/** Approximate wall duration from first/last event timestamps when available. */
export function durationFromEvents(events: ExecutionEvent[]): string {
  if (events.length === 0) return "—";
  const times = events
    .map((event) => new Date(event.occurred_at).getTime())
    .filter((value) => Number.isFinite(value));
  if (times.length < 2) return "—";
  return formatDurationMs(Math.max(...times) - Math.min(...times));
}

export function runStatusLabel(status: RunStatus): string {
  if (status === "created") return "Created";
  if (status === "queued") return "Queued";
  if (status === "running") return "Running";
  if (status === "grading") return "Grading";
  if (status === "completed") return "Completed";
  if (status === "failed") return "Failed";
  if (status === "cancelled") return "Cancelled";
  return status;
}

export function runStatusBadge(
  status: RunStatus,
): "neutral" | "queued" | "running" | "grading" | "completed" | "danger" | "cancelled" | "warning" {
  if (status === "queued" || status === "created") return "queued";
  if (status === "running") return "running";
  if (status === "grading") return "grading";
  if (status === "completed") return "completed";
  if (status === "failed") return "danger";
  if (status === "cancelled") return "cancelled";
  return "neutral";
}

export function canCancelRun(status: RunStatus): boolean {
  return status === "queued" || status === "running";
}

export function truncateId(id: string, size = 8): string {
  if (id.length <= size) return id;
  return `${id.slice(0, size)}…`;
}

export const RUN_STATUS_FILTERS = [
  { value: "", label: "All statuses" },
  { value: "queued", label: "Queued" },
  { value: "running", label: "Running" },
  { value: "grading", label: "Grading" },
  { value: "completed", label: "Completed" },
  { value: "failed", label: "Failed" },
  { value: "cancelled", label: "Cancelled" },
] as const;

export const runsQueryKey = ["runs"] as const;

export function runsListQueryKey(projectId: string) {
  return ["runs", "list", projectId] as const;
}

export function runQueryKey(runId: string) {
  return ["runs", runId] as const;
}

export function runEventsQueryKey(runId: string) {
  return ["runs", runId, "events"] as const;
}

export function runArtifactsQueryKey(runId: string) {
  return ["runs", runId, "artifacts"] as const;
}

export function runScoresQueryKey(runId: string) {
  return ["runs", runId, "scores"] as const;
}

export function sortEventsBySequence(events: ExecutionEvent[]): ExecutionEvent[] {
  return [...events].sort((a, b) => a.sequence - b.sequence);
}

export function pinsSummary(run: Run): string {
  const pins = run.pins;
  return [pins.case_version_id, pins.agent_version_id, pins.prompt_version_id].join(" ");
}
