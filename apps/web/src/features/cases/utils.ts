import type { Case, CaseVersion, PromptVersion } from "@/lib/api/cases";

export function formatCaseDate(value: string): string {
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

export function caseStatusLabel(status: Case["status"]): string {
  if (status === "deprecated") return "Deprecated";
  if (status === "active") return "Active";
  return status;
}

export function caseStatusBadge(status: Case["status"]): "success" | "neutral" | "warning" {
  if (status === "active") return "success";
  if (status === "deprecated") return "warning";
  return "neutral";
}

/** Shared by case versions and prompt versions: draft → active → superseded | retired */
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

export function casesQueryKey(projectId: string) {
  return ["projects", projectId, "cases"] as const;
}

export function caseQueryKey(caseId: string) {
  return ["cases", caseId] as const;
}

export function sortCaseVersionsNewestFirst(versions: CaseVersion[]): CaseVersion[] {
  return [...versions].sort((a, b) => {
    if (b.version_number !== a.version_number) {
      return b.version_number - a.version_number;
    }
    return b.created_at.localeCompare(a.created_at);
  });
}

export function sortPromptVersionsNewestFirst(versions: PromptVersion[]): PromptVersion[] {
  return [...versions].sort((a, b) => {
    if (b.version_number !== a.version_number) {
      return b.version_number - a.version_number;
    }
    return b.created_at.localeCompare(a.created_at);
  });
}

export function activeCaseVersion(caseItem: Case): CaseVersion | null {
  if (!caseItem.active_version_id) return null;
  return caseItem.versions.find((version) => version.id === caseItem.active_version_id) ?? null;
}

export function activePromptVersion(caseItem: Case): PromptVersion | null {
  if (!caseItem.active_prompt_version_id) return null;
  return (
    caseItem.prompt_versions.find((version) => version.id === caseItem.active_prompt_version_id) ??
    null
  );
}

/** Prompt versions that can be pinned by a case draft (not retired). */
export function pinnablePromptVersions(caseItem: Case): PromptVersion[] {
  return sortPromptVersionsNewestFirst(
    caseItem.prompt_versions.filter((version) => version.status !== "retired"),
  );
}

/**
 * Versions that a Run may pin (mirrors domain RunFactory): not draft, not retired.
 * Active and superseded are allowed.
 */
export function isPinnableVersionStatus(status: string): boolean {
  return status !== "draft" && status !== "retired";
}

/** Case versions eligible for run launch (active or superseded). */
export function pinnableCaseVersions(caseItem: Case): CaseVersion[] {
  return sortCaseVersionsNewestFirst(
    caseItem.versions.filter((version) => isPinnableVersionStatus(version.status)),
  );
}

/** Prompt versions eligible for run launch (active or superseded). */
export function pinnableRunPromptVersions(caseItem: Case): PromptVersion[] {
  return sortPromptVersionsNewestFirst(
    caseItem.prompt_versions.filter((version) => isPinnableVersionStatus(version.status)),
  );
}
