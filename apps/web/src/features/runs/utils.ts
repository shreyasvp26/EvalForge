import type { Artifact, ExecutionEvent, RunStatus, Score, ScoreValue } from "@/lib/api/runs";

export function formatRunDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(date);
}

export function formatRunTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
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
  const ms = durationMsFromEvents(events);
  return ms === null ? "—" : formatDurationMs(ms);
}

export function durationMsFromEvents(events: ExecutionEvent[]): number | null {
  if (events.length === 0) return null;
  const times = events
    .map((event) => new Date(event.occurred_at).getTime())
    .filter((value) => Number.isFinite(value));
  if (times.length < 2) return null;
  return Math.max(...times) - Math.min(...times);
}

export function elapsedMsSince(iso: string, nowMs: number = Date.now()): number | null {
  const started = new Date(iso).getTime();
  if (!Number.isFinite(started)) return null;
  return Math.max(0, nowMs - started);
}

export function runStartedAt(events: ExecutionEvent[], createdAt: string): string {
  if (events.length === 0) return createdAt;
  const times = events
    .map((event) => new Date(event.occurred_at).getTime())
    .filter((value) => Number.isFinite(value));
  if (times.length === 0) return createdAt;
  return new Date(Math.min(...times)).toISOString();
}

export function runFinishedAt(status: RunStatus, events: ExecutionEvent[]): string | null {
  if (!isTerminalRunStatus(status) || events.length === 0) return null;
  const times = events
    .map((event) => new Date(event.occurred_at).getTime())
    .filter((value) => Number.isFinite(value));
  if (times.length === 0) return null;
  return new Date(Math.max(...times)).toISOString();
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

/** Statuses that should keep the live refresh strategy active. */
export function isLiveRunStatus(status: RunStatus | undefined): boolean {
  return status === "queued" || status === "running" || status === "grading";
}

export function isTerminalRunStatus(status: RunStatus | undefined): boolean {
  return status === "completed" || status === "failed" || status === "cancelled";
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

export function pinsSummary(run: {
  pins: { case_version_id: string; agent_version_id: string; prompt_version_id: string };
}): string {
  const pins = run.pins;
  return [pins.case_version_id, pins.agent_version_id, pins.prompt_version_id].join(" ");
}

export type EventGroupId = "lifecycle" | "agent" | "output" | "grading" | "other";

export interface EventGroup {
  id: EventGroupId;
  label: string;
  events: ExecutionEvent[];
}

export function eventGroupId(kind: string): EventGroupId {
  const normalized = kind.toLowerCase();
  if (
    normalized.includes("queue") ||
    normalized.includes("status") ||
    normalized.includes("lifecycle") ||
    normalized.includes("sandbox") ||
    normalized.includes("cancel") ||
    normalized.includes("fail") ||
    normalized.includes("complete")
  ) {
    return "lifecycle";
  }
  if (
    normalized === "output" ||
    normalized.includes("stdout") ||
    normalized.includes("stderr") ||
    normalized.includes("log")
  ) {
    return "output";
  }
  if (
    normalized.includes("grade") ||
    normalized.includes("score") ||
    normalized.includes("rubric")
  ) {
    return "grading";
  }
  if (
    normalized === "tool_call" ||
    normalized === "file_edit" ||
    normalized === "shell_command" ||
    normalized === "message" ||
    normalized.includes("agent")
  ) {
    return "agent";
  }
  return "other";
}

const EVENT_GROUP_ORDER: EventGroupId[] = ["lifecycle", "agent", "output", "grading", "other"];

const EVENT_GROUP_LABELS: Record<EventGroupId, string> = {
  lifecycle: "Lifecycle",
  agent: "Agent activity",
  output: "Output",
  grading: "Grading",
  other: "Other",
};

/** Group sorted events while preserving sequence within each group. */
export function groupEvents(events: ExecutionEvent[]): EventGroup[] {
  const sorted = sortEventsBySequence(events);
  const buckets = new Map<EventGroupId, ExecutionEvent[]>();
  for (const id of EVENT_GROUP_ORDER) {
    buckets.set(id, []);
  }
  for (const event of sorted) {
    const id = eventGroupId(event.kind);
    buckets.get(id)?.push(event);
  }
  return EVENT_GROUP_ORDER.filter((id) => (buckets.get(id)?.length ?? 0) > 0).map((id) => ({
    id,
    label: EVENT_GROUP_LABELS[id],
    events: buckets.get(id) ?? [],
  }));
}

export function eventStatusBadge(
  kind: string,
): "neutral" | "queued" | "running" | "grading" | "completed" | "danger" | "cancelled" | "warning" {
  const group = eventGroupId(kind);
  if (group === "lifecycle") {
    const lower = kind.toLowerCase();
    if (lower.includes("fail")) return "danger";
    if (lower.includes("cancel")) return "cancelled";
    if (lower.includes("complete")) return "completed";
    if (lower.includes("queue")) return "queued";
    return "running";
  }
  if (group === "grading") return "grading";
  if (group === "output") return "neutral";
  if (group === "agent") return "running";
  return "neutral";
}

export function eventHeadline(event: ExecutionEvent): string {
  const action = event.action;
  const kindValue = action["kind"];
  const kind = typeof kindValue === "string" ? kindValue : event.kind;
  if (kind === "tool_call" && typeof action["tool_name"] === "string") {
    return `Tool · ${action["tool_name"]}`;
  }
  if (kind === "file_edit" && typeof action["path"] === "string") {
    return `Edit · ${action["path"]}`;
  }
  if (kind === "shell_command" && typeof action["command"] === "string") {
    return `Shell · ${action["command"]}`;
  }
  if (kind === "output" && typeof action["stream"] === "string") {
    return `Output · ${action["stream"]}`;
  }
  if (kind === "message" && typeof action["role"] === "string") {
    return `Message · ${action["role"]}`;
  }
  return event.kind;
}

export function eventSummary(event: ExecutionEvent): string | null {
  const action = event.action;
  const candidates = [
    action["content_summary"],
    action["result_summary"],
    action["diff_summary"],
    action["command"],
  ];
  for (const candidate of candidates) {
    if (typeof candidate === "string" && candidate.trim()) return candidate;
  }
  return null;
}

export function formatScoreValue(value: ScoreValue): string {
  const parts: string[] = [];
  if (value.numeric !== null) parts.push(String(value.numeric));
  if (value.categorical) parts.push(value.categorical);
  if (value.passed !== null) parts.push(value.passed ? "passed" : "failed");
  return parts.length > 0 ? parts.join(" · ") : "—";
}

export function scoreResultBadge(
  value: ScoreValue,
): "completed" | "danger" | "warning" | "neutral" | "grading" {
  if (value.passed === true) return "completed";
  if (value.passed === false) return "danger";
  if (value.numeric !== null) return "grading";
  if (value.categorical) return "neutral";
  return "neutral";
}

export type ArtifactTabId = "stdout" | "stderr" | "json" | "logs" | "files";

export const ARTIFACT_TABS: { id: ArtifactTabId; label: string }[] = [
  { id: "stdout", label: "stdout" },
  { id: "stderr", label: "stderr" },
  { id: "json", label: "JSON" },
  { id: "logs", label: "Logs" },
  { id: "files", label: "Files" },
];

export function artifactTabId(artifact: Artifact): ArtifactTabId {
  const kind = artifact.kind.toLowerCase();
  const type = artifact.content_type.toLowerCase();
  if (kind === "stdout") return "stdout";
  if (kind === "stderr") return "stderr";
  if (kind === "log" || kind === "transcript") return "logs";
  if (type.includes("json") || kind.includes("json") || kind === "rubric_explanation") {
    return "json";
  }
  if (kind === "diff" || kind === "other") return "files";
  if (type.startsWith("text/")) return "logs";
  return "files";
}

export function artifactsForTab(artifacts: Artifact[], tab: ArtifactTabId): Artifact[] {
  return artifacts.filter((artifact) => artifactTabId(artifact) === tab);
}

/** Build a readable preview from linked event summaries (API has no artifact body endpoint). */
export function artifactLinkedPreview(artifact: Artifact, events: ExecutionEvent[]): string | null {
  const linked = events.filter((event) => event.artifact_ids.includes(artifact.id));
  if (linked.length === 0) return null;
  const chunks = sortEventsBySequence(linked)
    .map((event) => {
      const summary = eventSummary(event);
      if (!summary) return null;
      return `#${String(event.sequence)} ${eventHeadline(event)}\n${summary}`;
    })
    .filter((value): value is string => Boolean(value));
  return chunks.length > 0 ? chunks.join("\n\n") : null;
}

export function artifactMetadataDocument(artifact: Artifact, preview: string | null): string {
  return JSON.stringify(
    {
      id: artifact.id,
      run_id: artifact.run_id,
      kind: artifact.kind,
      storage_key: artifact.storage_key,
      content_type: artifact.content_type,
      size_bytes: artifact.size_bytes,
      checksum: artifact.checksum,
      created_at: artifact.created_at,
      produced_by_grader_version_id: artifact.produced_by_grader_version_id,
      linked_preview: preview,
      note: "Full artifact bytes are not exposed by the Control Plane REST API yet. This file contains metadata and any linked event summaries.",
    },
    null,
    2,
  );
}

export function downloadTextFile(filename: string, contents: string, mime = "application/json") {
  const blob = new Blob([contents], { type: mime });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function formatByteSize(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes < 0) return "—";
  if (bytes < 1024) return `${String(bytes)} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function recentActivityLabel(events: ExecutionEvent[]): string | null {
  const sorted = sortEventsBySequence(events);
  const latest = sorted[sorted.length - 1];
  if (!latest) return null;
  return `${eventHeadline(latest)} · ${formatRunTime(latest.occurred_at)}`;
}

export function pendingGraderSlots(expected: number, scores: Score[]): number {
  return Math.max(0, expected - scores.length);
}
