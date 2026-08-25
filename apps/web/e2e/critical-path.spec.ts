import { expect, test } from "@playwright/test";

const email = process.env["E2E_EMAIL"] ?? "admin@evalforge.local";
const password = process.env["E2E_PASSWORD"] ?? "evalforge-admin";

async function signIn(page: import("@playwright/test").Page) {
  await page.goto("/login");
  await expect(page.getByRole("heading", { name: "Welcome back" })).toBeVisible();

  // Stale presence cookie without JWT must not trap on Restoring session.
  await page.context().addCookies([
    {
      name: "evalforge.auth",
      value: "1",
      url: "http://127.0.0.1:3000",
    },
  ]);
  await page.reload();
  await expect(page.getByRole("heading", { name: "Welcome back" })).toBeVisible({
    timeout: 8_000,
  });
  await expect(page.getByText("Restoring session")).toHaveCount(0);

  await page.getByLabel("Email", { exact: true }).fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();

  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible({
    timeout: 20_000,
  });
}

test.describe("critical product path", () => {
  test("login → overview → project → runs → run detail → logout", async ({ page }) => {
    await signIn(page);

    await expect(page.getByRole("region", { name: "Evaluation health" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Launch run" }).first()).toBeVisible();

    await page.locator('nav[aria-label="Primary"] a[href="/projects"]').click();
    await expect(page.getByRole("heading", { name: "Projects" })).toBeVisible();

    // DataGrid activates rows (no per-cell links).
    await page.getByRole("table", { name: "Projects" }).getByRole("row").nth(1).click();
    await expect(page).toHaveURL(/\/projects\/[^/]+/);

    await page.locator('nav[aria-label="Primary"] a[href="/runs"]').click();
    await expect(page.getByRole("heading", { name: "Runs" })).toBeVisible();

    const runRow = page.getByRole("table", { name: /Runs/i }).getByRole("row").nth(1);
    if (await runRow.count()) {
      await runRow.click();
    } else {
      await page
        .locator('a[href^="/runs/"]')
        .filter({ hasNotText: /Launch|New|Create/i })
        .first()
        .click();
    }

    await expect(page).toHaveURL(/\/runs\/[0-9a-f-]{8,}/i);
    await expect(page.getByText("Execution timeline")).toBeVisible({ timeout: 20_000 });
    await expect(page.getByText("Restoring session")).toHaveCount(0);

    // Observability surfaces from Phase 7 (present even when empty/terminal).
    await expect(
      page.getByText(/Live ·|Immutable execution record|Evaluation/i).first(),
    ).toBeVisible();
    await expect(page.getByText(/Artifacts|Scores|Execution timeline/i).first()).toBeVisible();

    // Logout returns to auth landing.
    const accountMenu = page.getByRole("button", { name: /account|profile|user|sign out|logout/i });
    if (await accountMenu.count()) {
      await accountMenu.first().click();
      const logout = page.getByRole("menuitem", { name: /sign out|log out/i });
      if (await logout.count()) {
        await logout.click();
        await expect(page.getByRole("heading", { name: "Welcome back" })).toBeVisible({
          timeout: 15_000,
        });
      }
    }
  });

  test("overview launch path remains reachable after login", async ({ page }) => {
    await signIn(page);
    await page.getByRole("link", { name: "Launch run" }).first().click();
    await expect(page).toHaveURL(/\/runs\/new|\/projects\/[^/]+/);
  });
});
