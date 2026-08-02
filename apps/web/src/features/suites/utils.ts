import type { Suite, SuiteVersion } from "@/lib/api/suites";

export function formatSuiteDate(value: string): string {
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

export function suiteStatusLabel(status: Suite["status"]): string {
  if (status === "deprecated") return "Deprecated";
  if (status === "active") return "Active";
  return status;
}

export function suiteStatusBadge(status: Suite["status"]): "success" | "neutral" | "warning" {
  if (status === "active") return "success";
  if (status === "deprecated") return "warning";
  return "neutral";
}

/** Version statuses: draft → active (publish) → superseded | retired */
export function versionStatusLabel(status: SuiteVersion["status"]): string {
  if (status === "draft") return "Draft";
  if (status === "active") return "Active";
  if (status === "superseded") return "Superseded";
  if (status === "retired") return "Retired";
  return status;
}

export function versionStatusBadge(
  status: SuiteVersion["status"],
): "neutral" | "success" | "warning" | "queued" | "cancelled" {
  if (status === "draft") return "queued";
  if (status === "active") return "success";
  if (status === "superseded") return "neutral";
  if (status === "retired") return "cancelled";
  return "warning";
}

export function suitesQueryKey(projectId: string) {
  return ["projects", projectId, "suites"] as const;
}

export function suiteQueryKey(suiteId: string) {
  return ["suites", suiteId] as const;
}

export function sortVersionsNewestFirst(versions: SuiteVersion[]): SuiteVersion[] {
  return [...versions].sort((a, b) => {
    if (b.version_number !== a.version_number) {
      return b.version_number - a.version_number;
    }
    return b.created_at.localeCompare(a.created_at);
  });
}

export function activeVersion(suite: Suite): SuiteVersion | null {
  if (!suite.active_version_id) return null;
  return suite.versions.find((version) => version.id === suite.active_version_id) ?? null;
}
