import { IconButton } from "./icon-button";
import { Search, Settings } from "../../icon/icons";

import type { Meta, StoryObj } from "@storybook/react";

const meta = {
  title: "Primitives/IconButton",
  component: IconButton,
  args: { icon: Search, label: "Search", size: "md", variant: "ghost" },
} satisfies Meta<typeof IconButton>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Ghost: Story = {};
export const Outline: Story = { args: { variant: "outline" } };
export const Secondary: Story = {
  args: { variant: "secondary", icon: Settings, label: "Settings" },
};
export const Small: Story = { args: { size: "sm" } };
export const Disabled: Story = { args: { disabled: true } };
