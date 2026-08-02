import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import type { StorybookConfig } from "@storybook/react-vite";

const dir = dirname(fileURLToPath(import.meta.url));

const config: StorybookConfig = {
  stories: [
    "../src/**/*.mdx",
    "../src/**/*.stories.@(ts|tsx)",
    "../../../apps/web/src/components/patterns/**/*.stories.@(ts|tsx)",
    "../../../apps/web/src/components/shell/**/*.stories.@(ts|tsx)",
  ],
  addons: ["@storybook/addon-essentials", "@storybook/addon-a11y"],
  framework: {
    name: "@storybook/react-vite",
    options: {},
  },
  async viteFinal(config) {
    const { default: react } = await import("@vitejs/plugin-react");
    const { default: tailwindcss } = await import("@tailwindcss/vite");
    config.plugins = [...(config.plugins ?? []), react(), tailwindcss()];
    config.resolve = {
      ...config.resolve,
      alias: {
        ...(config.resolve?.alias ?? {}),
        "@agent-eval/ui": join(dir, "../src"),
        "next/link": join(dir, "next-link-stub.tsx"),
      },
    };
    return config;
  },
};

export default config;
