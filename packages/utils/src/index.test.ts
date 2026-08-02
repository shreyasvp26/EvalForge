import { describe, expect, it } from "vitest";

import { createCorrelationId, invariant, isNonEmptyString, isUuid } from "./index.js";

describe("@agent-eval/utils", () => {
  it("creates uuid correlation ids", () => {
    const id = createCorrelationId();
    expect(isUuid(id)).toBe(true);
  });

  it("checks non-empty strings", () => {
    expect(isNonEmptyString(" a ")).toBe(true);
    expect(isNonEmptyString("   ")).toBe(false);
  });

  it("enforces invariants", () => {
    expect(() => {
      invariant(false, "nope");
    }).toThrow("nope");
  });
});
