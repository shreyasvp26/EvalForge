import type { Preview } from "@storybook/react";

import "../src/styles/tokens.css";

const preview: Preview = {
  parameters: {
    controls: { matchers: { color: /(background|color)$/i, date: /Date$/i } },
    layout: "centered",
    backgrounds: {
      default: "light",
      values: [
        { name: "light", value: "#fafafa" },
        { name: "dark", value: "#0a0a0b" },
      ],
    },
  },
};

export default preview;
