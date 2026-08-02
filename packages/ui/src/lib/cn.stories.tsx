import { cn } from "./cn.js";

import type { Meta, StoryObj } from "@storybook/react";

function CnDemo({ classes }: { classes: string }) {
  return (
    <code className={cn("rounded border px-2 py-1 font-mono text-sm", classes)}>
      {cn("base", classes)}
    </code>
  );
}

const meta = {
  title: "Foundation/cn",
  component: CnDemo,
  args: { classes: "text-blue-600" },
} satisfies Meta<typeof CnDemo>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
