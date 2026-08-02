import { defineConfig } from "vitest/config";

/**
 * Shared Vitest defaults for Node library packages.
 * Packages should spread or extend this rather than duplicating config.
 */
export const nodeVitestConfig = defineConfig({
  test: {
    environment: "node",
    include: ["src/**/*.{test,spec}.ts", "tests/**/*.{test,spec}.ts"],
    coverage: {
      provider: "v8",
      reporter: ["text", "lcov"],
      include: ["src/**/*.ts"],
      exclude: ["src/**/*.{test,spec}.ts", "src/**/index.ts"],
    },
    passWithNoTests: true,
  },
});

export default nodeVitestConfig;
