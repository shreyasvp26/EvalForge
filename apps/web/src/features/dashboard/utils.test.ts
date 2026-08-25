import { describe, expect, it } from "vitest";

import { buildEvaluationHealth, formatRelativeTime, runPassSignal } from "./utils";

import type { Run } from "@/lib/api/runs";

function makeRun(partial: Partial<Run> & Pick<Run, "id" | "status">): Run {
  return {
    created_at: "2026-01-01T00:00:00.000Z",
    pins: {
      project_id: "proj-1",
      case_version_id: "cv-1",
      prompt_version_id: "pv-1",
      agent_version_id: "av-1",
      adapter_version_id: "adv-1",
      platform_version_id: "plat-1",
      grader_version_ids: [],
      suite_version_id: null,
    },
    failure_reason: null,
    failure_category: null,
    cancellation_reason: null,
    sandbox_id: null,
    expected_grader_count: 1,
    produced_score_count: 0,
    is_partially_graded: false,
    scores: [],
    ...partial,
  };
}

describe("dashboard evaluation health", () => {
  it("counts active and terminal outcomes from real run statuses", () => {
    const health = buildEvaluationHealth([
      makeRun({ id: "1", status: "running" }),
      makeRun({ id: "2", status: "queued" }),
      makeRun({
        id: "3",
        status: "completed",
        scores: [
          {
            id: "s1",
            grader_id: "g1",
            grader_version_id: "gv1",
            value: { numeric: 1, categorical: null, passed: true },
            explanation_artifact_id: null,
          },
        ],
      }),
      makeRun({ id: "4", status: "failed", failure_reason: "timeout" }),
    ]);

    expect(health.active).toBe(2);
    expect(health.passed).toBe(1);
    expect(health.failed).toBe(1);
    expect(health.sampledRuns).toBe(4);
  });

  it("derives pass signal only from score data", () => {
    expect(runPassSignal(makeRun({ id: "x", status: "completed" }))).toBeNull();
    expect(
      runPassSignal(
        makeRun({
          id: "y",
          status: "completed",
          scores: [
            {
              id: "s1",
              grader_id: "g1",
              grader_version_id: "gv1",
              value: { numeric: 0, categorical: null, passed: false },
              explanation_artifact_id: null,
            },
          ],
        }),
      ),
    ).toBe(false);
  });

  it("formats relative time from real timestamps", () => {
    const recent = new Date(Date.now() - 90_000).toISOString();
    expect(formatRelativeTime(recent)).toMatch(/minute/);
  });
});
