import { DetailSkeleton } from "./detail-skeleton";
import { FormSkeleton } from "./form-skeleton";
import { GlobalLoading } from "./global-loading";
import { PageSkeleton } from "./page-skeleton";
import { TableSkeleton } from "./table-skeleton";

import type { Meta, StoryObj } from "@storybook/react";

const meta = {
  title: "Product Patterns/Loading",
  parameters: { layout: "padded" },
} satisfies Meta;

export default meta;
type Story = StoryObj;

export const Page: Story = {
  render: () => (
    <div className="w-[640px]">
      <PageSkeleton />
    </div>
  ),
};

export const Table: Story = {
  render: () => (
    <div className="w-[640px]">
      <TableSkeleton />
    </div>
  ),
};

export const Detail: Story = {
  render: () => (
    <div className="w-[720px]">
      <DetailSkeleton />
    </div>
  ),
};

export const Form: Story = {
  render: () => <FormSkeleton />,
};

export const Global: Story = {
  parameters: { layout: "fullscreen" },
  render: () => (
    <div className="relative h-[360px] w-full overflow-hidden bg-background">
      <GlobalLoading label="Loading workspace" />
    </div>
  ),
};
