import path from "node:path";
import { fileURLToPath } from "node:url";

import { defineConfig, mergeConfig } from "vitest/config";

import { nodeVitestConfig } from "@agent-eval/config/vitest/node.js";

const root = path.dirname(fileURLToPath(import.meta.url));

export default mergeConfig(
  nodeVitestConfig,
  defineConfig({
    resolve: {
      alias: {
        "@": path.join(root, "src"),
      },
    },
  }),
);
