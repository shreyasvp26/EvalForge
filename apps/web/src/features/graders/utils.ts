import type { Grader, GraderVersion } from "@/lib/api/graders";

export function formatGraderDate(value: string): string {
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

export function entityStatusLabel(status: string): string {
  if (status === "deprecated") return "Deprecated";
  if (status === "active") return "Active";
  return status;
}

export function entityStatusBadge(status: string): "success" | "neutral" | "warning" {
  if (status === "active") return "success";
  if (status === "deprecated") return "warning";
  return "neutral";
}

export function versionStatusLabel(status: string): string {
  if (status === "draft") return "Draft";
  if (status === "active") return "Active";
  if (status === "superseded") return "Superseded";
  if (status === "retired") return "Retired";
  return status;
}

export function versionStatusBadge(
  status: string,
): "neutral" | "success" | "warning" | "queued" | "cancelled" {
  if (status === "draft") return "queued";
  if (status === "active") return "success";
  if (status === "superseded") return "neutral";
  if (status === "retired") return "cancelled";
  return "warning";
}

/** Distinguish grader families with existing Badge status tokens. */
export function familyStatusBadge(family: string): "completed" | "grading" | "neutral" {
  const normalized = family.trim().toLowerCase();
  if (normalized === "objective") return "completed";
  if (normalized === "rubric") return "grading";
  return "neutral";
}

export function familyStatusLabel(family: string): string {
  const normalized = family.trim().toLowerCase();
  if (normalized === "objective") return "Objective";
  if (normalized === "rubric") return "Rubric";
  return family;
}

export const GRADER_FAMILIES = [
  { value: "objective", label: "Objective" },
  { value: "rubric", label: "Rubric" },
] as const;

export const gradersQueryKey = ["graders"] as const;

export function graderQueryKey(graderId: string) {
  return ["graders", graderId] as const;
}

export function sortGraderVersionsNewestFirst(versions: GraderVersion[]): GraderVersion[] {
  return [...versions].sort((a, b) => {
    if (b.version_number !== a.version_number) {
      return b.version_number - a.version_number;
    }
    return b.created_at.localeCompare(a.created_at);
  });
}

export function activeGraderVersion(grader: Grader): GraderVersion | null {
  if (!grader.active_version_id) return null;
  return grader.versions.find((version) => version.id === grader.active_version_id) ?? null;
}
