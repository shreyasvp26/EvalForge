import type { Project } from "@/lib/api/projects";

export function formatProjectDate(value: string): string {
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

export function projectStatusLabel(status: Project["status"]): string {
  if (status === "deprecated") return "Deprecated";
  if (status === "active") return "Active";
  return status;
}

export function projectStatusBadge(status: Project["status"]): "success" | "neutral" | "warning" {
  if (status === "active") return "success";
  if (status === "deprecated") return "warning";
  return "neutral";
}

export const projectsQueryKey = ["projects"] as const;

export function projectQueryKey(projectId: string) {
  return ["projects", projectId] as const;
}
