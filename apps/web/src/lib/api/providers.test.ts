import { describe, expect, it } from "vitest";

import { isGeminiAdapterPath } from "@/lib/api/providers";

describe("isGeminiAdapterPath", () => {
  it("detects gemini adapter names", () => {
    expect(isGeminiAdapterPath("gemini_cli")).toBe(true);
    expect(isGeminiAdapterPath("Gemini CLI")).toBe(true);
    expect(isGeminiAdapterPath("gemini")).toBe(true);
  });

  it("rejects unrelated adapters", () => {
    expect(isGeminiAdapterPath("claude_code")).toBe(false);
    expect(isGeminiAdapterPath(null)).toBe(false);
    expect(isGeminiAdapterPath("")).toBe(false);
  });
});
