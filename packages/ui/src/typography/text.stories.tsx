import { Text } from "./text";

import type { Meta, StoryObj } from "@storybook/react";

const meta = {
  title: "Typography/Text",
  component: Text,
  args: {
    children: "Immutable evaluation runs with full lineage and reproducible grading.",
    variant: "body",
  },
} satisfies Meta<typeof Text>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Body: Story = {};

export const Secondary: Story = {
  args: { variant: "secondary" },
};

export const Caption: Story = {
  args: { variant: "caption", children: "Updated 2 minutes ago" },
};

export const Code: Story = {
  args: { variant: "code", children: "run_01HZX…" },
};

export const TableLabel: Story = {
  args: { variant: "table", children: "Status" },
};
