import { defineConfig, devices } from "@playwright/test";

const baseURL = process.env["PLAYWRIGHT_BASE_URL"] ?? "http://127.0.0.1:3000";

/**
 * Critical-path browser coverage for EvalForge web.
 * Requires a running web app (+ API for authenticated flows).
 *
 *   PLAYWRIGHT_BASE_URL=http://127.0.0.1:3000 \
 *   E2E_EMAIL=admin@evalforge.local \
 *   E2E_PASSWORD=evalforge-admin \
 *   pnpm --filter @agent-eval/web test:e2e
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: Boolean(process.env["CI"]),
  retries: process.env["CI"] ? 1 : 0,
  workers: 1,
  timeout: 60_000,
  expect: { timeout: 15_000 },
  reporter: [["list"]],
  use: {
    baseURL,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    ...devices["Desktop Chrome"],
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
