import { describe, expect, it } from "vitest";

import {
  eventHeadline,
  formatDurationMs,
  groupEvents,
  runPassSignal,
  sortEventsBySequence,
} from "./utils";

import type { ExecutionEvent, Run } from "@/lib/api/runs";

function event(
  partial: Partial<ExecutionEvent> & Pick<ExecutionEvent, "id" | "sequence" | "kind">,
): ExecutionEvent {
  return {
    run_id: "run-1",
    action: {},
    artifact_ids: [],
    occurred_at: "2026-01-01T00:00:00.000Z",
    metadata: {},
    ...partial,
  };
}

describe("runs utils", () => {
  it("sorts and groups execution events for the timeline", () => {
    const events = sortEventsBySequence([
      event({ id: "2", sequence: 2, kind: "tool_call", action: { tool_name: "bash" } }),
      event({ id: "1", sequence: 1, kind: "lifecycle.status" }),
      event({ id: "3", sequence: 3, kind: "grading.score" }),
    ]);
    expect(events.map((item) => item.id)).toEqual(["1", "2", "3"]);
    const groups = groupEvents(events);
    expect(groups.map((group) => group.id)).toEqual(["lifecycle", "agent", "grading"]);
    const toolEvent = events.find((item) => item.id === "2");
    expect(toolEvent).toBeDefined();
    if (!toolEvent) throw new Error("expected tool event");
    expect(eventHeadline(toolEvent)).toBe("Tool · bash");
  });

  it("formats durations and pass signals from score data", () => {
    expect(formatDurationMs(1500)).toBe("1.5s");
    const run = {
      scores: [
        {
          id: "s1",
          grader_id: "g1",
          grader_version_id: "gv1",
          value: { numeric: 1, categorical: null, passed: true },
          explanation_artifact_id: null,
        },
      ],
    } as Pick<Run, "scores">;
    expect(runPassSignal(run)).toBe(true);
  });
});
