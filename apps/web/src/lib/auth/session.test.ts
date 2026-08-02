import { describe, expect, it } from "vitest";

import { hasSessionCookie } from "./session";

describe("hasSessionCookie", () => {
  it("detects the session presence cookie", () => {
    expect(hasSessionCookie("evalforge.auth=1; theme=dark")).toBe(true);
    expect(hasSessionCookie("theme=dark")).toBe(false);
    expect(hasSessionCookie(null)).toBe(false);
  });
});
