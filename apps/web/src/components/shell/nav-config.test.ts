import { describe, expect, it } from "vitest";

import { breadcrumbsForPath, isNavActive, navSections, primaryNavItems } from "./nav-config";

describe("nav-config", () => {
  it("groups primary navigation into workspace, evaluation, and system", () => {
    expect(navSections.map((section) => section.id)).toEqual(["workspace", "evaluation", "system"]);
    expect(primaryNavItems.map((item) => item.href)).toEqual([
      "/",
      "/projects",
      "/runs",
      "/benchmarks",
      "/agents",
      "/graders",
      "/settings",
    ]);
  });

  it("keeps design system out of primary product navigation", () => {
    expect(primaryNavItems.some((item) => item.href === "/design-system")).toBe(false);
  });

  it("marks overview active only on the root path", () => {
    expect(isNavActive("/", "/")).toBe(true);
    expect(isNavActive("/projects", "/")).toBe(false);
  });

  it("builds shell breadcrumbs from EvalForge root", () => {
    expect(breadcrumbsForPath("/")).toEqual([
      { label: "EvalForge", href: "/" },
      { label: "Overview" },
    ]);
    expect(breadcrumbsForPath("/runs")).toEqual([
      { label: "EvalForge", href: "/" },
      { label: "Runs" },
    ]);
    expect(breadcrumbsForPath("/runs/abc")).toEqual([
      { label: "EvalForge", href: "/" },
      { label: "Runs", href: "/runs" },
      { label: "Run" },
    ]);
  });
});
