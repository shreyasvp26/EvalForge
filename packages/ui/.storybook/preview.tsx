import type { Preview } from "@storybook/react";

import "./preview.css";

const preview: Preview = {
  parameters: {
    controls: { matchers: { color: /(background|color)$/i, date: /Date$/i } },
    layout: "centered",
    backgrounds: {
      default: "light",
      values: [
        { name: "light", value: "#f7f7f8" },
        { name: "dark", value: "#0b0b0c" },
      ],
    },
  },
  decorators: [
    (Story, context) => {
      const isDark = context.globals["backgrounds"]?.value === "#0b0b0c";
      return (
        <div className={isDark ? "dark" : undefined} style={{ color: "var(--ef-foreground)" }}>
          <Story />
        </div>
      );
    },
  ],
};

export default preview;
