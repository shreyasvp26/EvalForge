import { Icon } from "./icon";
import { Search, Settings, Loader2 } from "./icons";

import type { Meta, StoryObj } from "@storybook/react";

const meta = {
  title: "Foundation/Icon",
  component: Icon,
  args: {
    icon: Search,
    size: "md",
  },
} satisfies Meta<typeof Icon>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const Labeled: Story = {
  args: {
    icon: Settings,
    "aria-label": "Settings",
  },
};

export const Loading: Story = {
  args: {
    icon: Loader2,
    className: "animate-spin",
    "aria-label": "Loading",
  },
};
