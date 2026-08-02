import { ConfigurationError } from "@agent-eval/errors";
import { describe, expect, it } from "vitest";

import { baseEnvSchema, loadEnv } from "./index.js";

describe("@agent-eval/env", () => {
  it("loads defaults for baseline schema", () => {
    const env = loadEnv(baseEnvSchema, { source: {} });
    expect(env.NODE_ENV).toBe("development");
    expect(env.LOG_LEVEL).toBe("info");
  });

  it("fails fast on invalid values", () => {
    expect(() =>
      loadEnv(baseEnvSchema, {
        source: { NODE_ENV: "staging", LOG_LEVEL: "info" },
      }),
    ).toThrow(ConfigurationError);
  });
});
