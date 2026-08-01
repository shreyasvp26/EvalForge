import baseConfig from "@agent-eval/config/eslint/base.js";

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
    ],
  },
  ...baseConfig,
];
