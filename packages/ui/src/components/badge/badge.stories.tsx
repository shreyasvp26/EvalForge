import { Badge } from "./badge";

import type { Meta, StoryObj } from "@storybook/react";

const meta = {
  title: "Feedback/Badge",
  component: Badge,
  args: { children: "Running", status: "running" },
} satisfies Meta<typeof Badge>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Running: Story = {};
export const Success: Story = { args: { status: "success", children: "Passed" } };
export const Danger: Story = { args: { status: "danger", children: "Failed" } };
export const Grading: Story = { args: { status: "grading", children: "Grading" } };
export const Queued: Story = { args: { status: "queued", children: "Queued" } };
