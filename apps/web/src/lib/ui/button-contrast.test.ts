import { describe, expect, it } from "vitest";

/** Relative luminance for sRGB hex (#rrggbb). */
function luminance(hex: string): number {
  const raw = hex.replace("#", "");
  const channels = [0, 1, 2].map((i) => {
    const c = Number.parseInt(raw.slice(i * 2, i * 2 + 2), 16) / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * (channels[0] ?? 0) + 0.7152 * (channels[1] ?? 0) + 0.0722 * (channels[2] ?? 0);
}

function contrastRatio(fg: string, bg: string): number {
  const a = luminance(fg);
  const b = luminance(bg);
  const lighter = Math.max(a, b);
  const darker = Math.min(a, b);
  return (lighter + 0.05) / (darker + 0.05);
}

describe("primary button accent contrast", () => {
  it("light theme accent meets AA for normal text", () => {
    expect(contrastRatio("#ffffff", "#7c3aed")).toBeGreaterThanOrEqual(4.5);
  });

  it("dark theme accent meets AA for normal text", () => {
    expect(contrastRatio("#ffffff", "#8b5cf6")).toBeGreaterThanOrEqual(4.5);
  });
});
