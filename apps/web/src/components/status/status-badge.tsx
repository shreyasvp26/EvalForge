import {
  Badge,
  Ban,
  CheckCircle2,
  Circle,
  Clock,
  cn,
  Icon,
  Loader2,
  XCircle,
} from "@agent-eval/ui";

import type { RunStatus } from "@/lib/api/runs";
import type { LucideIcon } from "@agent-eval/ui";

type StatusTone =
  "neutral" | "queued" | "running" | "grading" | "completed" | "danger" | "cancelled" | "warning";

export interface RunStatusMeta {
  label: string;
  tone: StatusTone;
  icon: LucideIcon;
  /** Short verb for live surfaces ("Running", not decorative). */
  liveLabel?: string;
}

const STATUS_META: Record<string, RunStatusMeta> = {
  created: { label: "Created", tone: "queued", icon: Circle },
  queued: { label: "Queued", tone: "queued", icon: Clock, liveLabel: "Waiting" },
  running: { label: "Running", tone: "running", icon: Loader2, liveLabel: "In progress" },
  grading: { label: "Grading", tone: "grading", icon: Loader2, liveLabel: "Scoring" },
  completed: { label: "Completed", tone: "completed", icon: CheckCircle2 },
  failed: { label: "Failed", tone: "danger", icon: XCircle },
  cancelled: { label: "Cancelled", tone: "cancelled", icon: Ban },
};

/** Prefer "Passed" for successful completed runs when a score confirms pass. */
export function resolveRunStatusMeta(
  status: RunStatus,
  options?: { passed?: boolean | null },
): RunStatusMeta {
  if (status === "completed" && options?.passed === false) {
    return { label: "Failed", tone: "danger", icon: XCircle };
  }
  if (status === "completed" && options?.passed === true) {
    return { label: "Passed", tone: "completed", icon: CheckCircle2 };
  }
  if (status === "completed" && options?.passed == null) {
    return { label: "Completed", tone: "completed", icon: CheckCircle2 };
  }
  return STATUS_META[status] ?? { label: status, tone: "neutral", icon: Circle };
}

export function runStatusLabel(status: RunStatus, options?: { passed?: boolean | null }): string {
  return resolveRunStatusMeta(status, options).label;
}

export function runStatusTone(
  status: RunStatus,
  options?: { passed?: boolean | null },
): StatusTone {
  return resolveRunStatusMeta(status, options).tone;
}

export interface StatusBadgeProps {
  status: RunStatus;
  /** When known from scores, refine completed → Passed/Failed. */
  passed?: boolean | null;
  /** Show spinning icon for live statuses. */
  animate?: boolean;
  className?: string;
  /** Visually denser for tables. */
  size?: "sm" | "md";
}

/**
 * Status indicator that never relies on color alone — label + icon + tone.
 */
export function StatusBadge({
  status,
  passed,
  animate = true,
  className,
  size = "md",
}: StatusBadgeProps) {
  const meta = resolveRunStatusMeta(status, passed === undefined ? undefined : { passed });
  const spinning =
    animate && (status === "running" || status === "grading") && meta.icon === Loader2;

  return (
    <Badge
      status={meta.tone}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-[var(--ef-radius-control)] font-medium",
        size === "sm" ? "px-1.5 py-0" : "px-2 py-0.5",
        className,
      )}
    >
      <Icon
        icon={meta.icon}
        size="xs"
        className={cn(spinning && "animate-spin motion-reduce:animate-none")}
        aria-hidden
      />
      <span>{meta.label}</span>
    </Badge>
  );
}
