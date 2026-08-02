import { Button } from "./button";
import { Plus } from "../../icon/icons";

import type { Meta, StoryObj } from "@storybook/react";

const meta = {
  title: "Primitives/Button",
  component: Button,
  args: { children: "Create run", variant: "primary", size: "md" },
} satisfies Meta<typeof Button>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Primary: Story = {};
export const Secondary: Story = { args: { variant: "secondary" } };
export const Outline: Story = { args: { variant: "outline" } };
export const Ghost: Story = { args: { variant: "ghost" } };
export const Danger: Story = { args: { variant: "danger", children: "Delete" } };
export const Loading: Story = { args: { loading: true, children: "Saving" } };
export const Disabled: Story = { args: { disabled: true } };
export const WithIcon: Story = { args: { leftIcon: Plus } };
