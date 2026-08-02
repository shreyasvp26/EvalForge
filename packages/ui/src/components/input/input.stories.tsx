import { Input } from "./input";

import type { Meta, StoryObj } from "@storybook/react";

const meta = {
  title: "Forms/Input",
  component: Input,
  args: { placeholder: "Search runs…", "aria-label": "Search" },
} satisfies Meta<typeof Input>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const Disabled: Story = { args: { disabled: true, value: "Locked" } };
