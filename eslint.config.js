import { dirname } from "node:path";
import { fileURLToPath } from "node:url";

import { createEslintConfig } from "@agent-eval/config/eslint/base.js";

const tsconfigRootDir = dirname(fileURLToPath(import.meta.url));

/** @type {import("eslint").Linter.Config[]} */
export default [
  {
    ignores: [
      "**/node_modules/**",
      "**/dist/**",
      "**/build/**",
      "**/.next/**",
      "**/.turbo/**",
      "**/.venv/**",
      "**/coverage/**",
      "**/vitest.config.ts",
      "**/uv.lock",
      "**/pnpm-lock.yaml",
    ],
  },
  ...createEslintConfig({ tsconfigRootDir }),
];
