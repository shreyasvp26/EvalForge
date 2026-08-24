import { describe, expect, it } from "vitest";

import { resolveRunStatusMeta, runStatusLabel } from "./status-badge";

describe("status-badge", () => {
  it("exposes human labels that do not rely on color alone", () => {
    expect(runStatusLabel("queued")).toBe("Queued");
    expect(runStatusLabel("running")).toBe("Running");
    expect(runStatusLabel("grading")).toBe("Grading");
    expect(runStatusLabel("failed")).toBe("Failed");
    expect(runStatusLabel("cancelled")).toBe("Cancelled");
  });

  it("refines completed status when pass/fail is known", () => {
    expect(runStatusLabel("completed", { passed: true })).toBe("Passed");
    expect(runStatusLabel("completed", { passed: false })).toBe("Failed");
    expect(runStatusLabel("completed")).toBe("Completed");
  });

  it("pairs every status with an icon tone", () => {
    const meta = resolveRunStatusMeta("running");
    expect(meta.tone).toBe("running");
    expect(meta.icon).toBeTruthy();
  });
});
