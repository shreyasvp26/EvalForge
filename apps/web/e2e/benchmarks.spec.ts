import { expect, test } from "@playwright/test";

const email = process.env["E2E_EMAIL"] ?? "admin@evalforge.local";
const password = process.env["E2E_PASSWORD"] ?? "evalforge-admin";

async function signIn(page: import("@playwright/test").Page) {
  await page.goto("/login");
  await expect(page.getByRole("heading", { name: "Welcome back" })).toBeVisible();
  await page.getByLabel("Email", { exact: true }).fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible({
    timeout: 20_000,
  });
}

/**
 * UI E2E for the benchmark critical path (deterministic; does not invoke live Gemini).
 * Requires seeded catalog data for at least one project.
 */
test.describe("benchmark catalog path", () => {
  test("login → benchmarks → open coding benchmark → configure review", async ({ page }) => {
    await signIn(page);

    await page.locator('nav[aria-label="Primary"] a[href="/benchmarks"]').click();
    await expect(page.getByRole("heading", { name: "Benchmarks" })).toBeVisible({
      timeout: 15_000,
    });

    const openProject = page.getByRole("link", { name: /Open benchmarks/i }).first();
    if ((await openProject.count()) === 0) {
      test.skip(true, "No projects available for benchmark catalog UI");
      return;
    }
    await openProject.click();
    await expect(page.getByRole("heading", { name: "Benchmarks" })).toBeVisible();

    const coding = page.getByText(/coding-benchmark-v1|Coding Benchmark/i).first();
    if ((await coding.count()) === 0) {
      test.skip(true, "Coding Benchmark v1 not seeded in this environment");
      return;
    }

    await page.getByRole("link", { name: "Open" }).first().click();
    await expect(page.getByText("Configure execution")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText("Review execution")).toBeVisible();
    await expect(page.getByText(/Workspace pytest/i).first()).toBeVisible();
  });
});
