import { describe, expect, it } from "vitest";

import { SETTINGS_NAV } from "./settings-nav";

describe("SETTINGS_NAV", () => {
  it("includes Providers and GitHub under settings", () => {
    const hrefs = SETTINGS_NAV.map((item) => item.href);
    expect(hrefs).toContain("/settings/providers");
    expect(hrefs).toContain("/settings/github");
    expect(hrefs).toContain("/settings/profile");
    expect(hrefs).toContain("/settings/api");
  });
});
