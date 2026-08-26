import { describe, expect, it } from "vitest";

import { buildOAuthAuthorizeUrl } from "@/lib/auth/oauth";

describe("buildOAuthAuthorizeUrl", () => {
  it("includes provider path and next query", () => {
    expect(buildOAuthAuthorizeUrl("google", "/overview", "http://localhost:8000")).toBe(
      "http://localhost:8000/v1/auth/google/authorize?next=%2Foverview",
    );
  });

  it("omits next when landing page is root", () => {
    expect(buildOAuthAuthorizeUrl("github", "/", "http://localhost:8000")).toBe(
      "http://localhost:8000/v1/auth/github/authorize",
    );
  });
});
