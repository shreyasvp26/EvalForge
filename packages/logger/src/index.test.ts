import { describe, expect, it } from "vitest";

import { createLogger, getLogContext, withLogContext } from "./index.js";

describe("@agent-eval/logger", () => {
  it("attaches correlation context for the duration of a scope", () => {
    const logger = createLogger({ environment: "test", level: "silent" });
    expect(logger.level).toBe("silent");

    withLogContext({ correlationId: "cid-1", runId: "run-1" }, () => {
      expect(getLogContext()).toMatchObject({
        correlationId: "cid-1",
        runId: "run-1",
      });
    });

    expect(getLogContext()).toBeUndefined();
  });
});
