import { Heading } from "./heading";

import type { Meta, StoryObj } from "@storybook/react";

const meta = {
  title: "Typography/Heading",
  component: Heading,
  args: {
    children: "Evaluation runs",
    variant: "page",
  },
} satisfies Meta<typeof Heading>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Page: Story = {};

export const Display: Story = {
  args: { variant: "display", children: "EvalForge" },
};

export const Section: Story = {
  args: { variant: "section", children: "Suites" },
};

export const Card: Story = {
  args: { variant: "card", children: "Pass rate" },
};
