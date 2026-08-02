import { describe, expect, it } from "vitest";

import {
  ApplicationError,
  ConfigurationError,
  InfrastructureError,
  ValidationError,
  isAppError,
  serializeError,
} from "./index.js";

describe("@agent-eval/errors", () => {
  it("serializes typed errors with code and retryable", () => {
    const error = new InfrastructureError({
      code: "DB_UNAVAILABLE",
      message: "connection refused",
      retryable: true,
      details: { host: "db" },
    });

    expect(isAppError(error)).toBe(true);
    expect(error.toJSON()).toMatchObject({
      name: "InfrastructureError",
      code: "DB_UNAVAILABLE",
      retryable: true,
      details: { host: "db" },
    });
  });

  it("marks validation and configuration errors as not retryable", () => {
    expect(new ValidationError({ code: "INVALID", message: "bad" }).retryable).toBe(false);
    expect(
      new ConfigurationError({ code: "INVALID_CONFIGURATION", message: "bad" }).retryable,
    ).toBe(false);
    expect(new ApplicationError({ code: "FORBIDDEN", message: "no" }).retryable).toBe(false);
  });

  it("serializes unknown errors safely", () => {
    expect(serializeError(new Error("boom"))).toMatchObject({
      code: "UNTYPED_ERROR",
      message: "boom",
      retryable: false,
    });
  });
});
