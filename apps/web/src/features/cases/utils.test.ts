import { describe, expect, it } from "vitest";

import { isPinnableVersionStatus, pinnableCaseVersions, pinnableRunPromptVersions } from "./utils";

import type { Case } from "@/lib/api/cases";

function sampleCase(overrides: Partial<Case> = {}): Case {
  return {
    id: "case-1",
    project_id: "proj-1",
    prompt_id: "p1",
    name: "Sample",
    description: "Sample case",
    status: "active",
    created_at: "2026-01-01T00:00:00.000Z",
    active_version_id: "cv-active",
    active_prompt_version_id: "pv-active",
    versions: [
      {
        id: "cv-draft",
        case_id: "case-1",
        version_number: 3,
        status: "draft",
        description: "draft",
        repository_url: "https://example.com/repo",
        commit_sha: "abc",
        subdirectory: null,
        expected_checks: [],
        applicable_grader_ids: ["g1"],
        prompt_version_id: "pv-active",
        predecessor_version_id: "cv-active",
        created_at: "2026-01-03T00:00:00.000Z",
      },
      {
        id: "cv-active",
        case_id: "case-1",
        version_number: 2,
        status: "active",
        description: "active",
        repository_url: "https://example.com/repo",
        commit_sha: "abc",
        subdirectory: null,
        expected_checks: [],
        applicable_grader_ids: ["g1"],
        prompt_version_id: "pv-active",
        predecessor_version_id: "cv-old",
        created_at: "2026-01-02T00:00:00.000Z",
      },
      {
        id: "cv-retired",
        case_id: "case-1",
        version_number: 1,
        status: "retired",
        description: "retired",
        repository_url: "https://example.com/repo",
        commit_sha: "abc",
        subdirectory: null,
        expected_checks: [],
        applicable_grader_ids: [],
        prompt_version_id: "pv-retired",
        predecessor_version_id: null,
        created_at: "2026-01-01T00:00:00.000Z",
      },
    ],
    prompt_versions: [
      {
        id: "pv-draft",
        prompt_id: "p1",
        version_number: 3,
        status: "draft",
        content: "draft prompt",
        predecessor_version_id: "pv-active",
        created_at: "2026-01-03T00:00:00.000Z",
      },
      {
        id: "pv-active",
        prompt_id: "p1",
        version_number: 2,
        status: "active",
        content: "active prompt",
        predecessor_version_id: "pv-old",
        created_at: "2026-01-02T00:00:00.000Z",
      },
      {
        id: "pv-superseded",
        prompt_id: "p1",
        version_number: 1,
        status: "superseded",
        content: "old prompt",
        predecessor_version_id: null,
        created_at: "2026-01-01T00:00:00.000Z",
      },
    ],
    ...overrides,
  };
}

describe("case pinnable helpers", () => {
  it("treats active and superseded as pinnable for runs", () => {
    expect(isPinnableVersionStatus("active")).toBe(true);
    expect(isPinnableVersionStatus("superseded")).toBe(true);
    expect(isPinnableVersionStatus("draft")).toBe(false);
    expect(isPinnableVersionStatus("retired")).toBe(false);
  });

  it("filters case and prompt versions for run launch", () => {
    const caseItem = sampleCase();
    expect(pinnableCaseVersions(caseItem).map((v) => v.id)).toEqual(["cv-active"]);
    expect(pinnableRunPromptVersions(caseItem).map((v) => v.id)).toEqual([
      "pv-active",
      "pv-superseded",
    ]);
  });
});
