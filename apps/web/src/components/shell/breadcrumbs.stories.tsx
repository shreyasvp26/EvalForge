import { Breadcrumbs } from "./breadcrumbs";

import type { Meta, StoryObj } from "@storybook/react";

const meta = {
  title: "Product Patterns/Navigation",
  component: Breadcrumbs,
  parameters: { layout: "padded" },
} satisfies Meta<typeof Breadcrumbs>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: {
    items: [
      { label: "Workspace", href: "/" },
      { label: "Projects", href: "/" },
      { label: "Current page" },
    ],
  },
};
