import { Button } from "@agent-eval/ui";

import { ComingSoonState } from "./coming-soon-state";
import { NoResultsState } from "./no-results-state";
import { NotFoundState } from "./not-found-state";
import { PermissionDeniedState } from "./permission-denied-state";
import { SearchEmptyState } from "./search-empty-state";
import { SuccessState } from "./success-state";

import type { Meta, StoryObj } from "@storybook/react";

const meta = {
  title: "Product Patterns/Empty & Status",
  parameters: { layout: "padded" },
} satisfies Meta;

export default meta;
type Story = StoryObj;

export const SearchEmpty: Story = {
  render: () => (
    <div className="w-[420px]">
      <SearchEmptyState
        query="xyzzy"
        action={
          <Button size="sm" variant="outline">
            Clear search
          </Button>
        }
      />
    </div>
  ),
};

export const NoResults: Story = {
  render: () => (
    <div className="w-[420px]">
      <NoResultsState
        action={
          <Button size="sm" variant="outline">
            Clear filters
          </Button>
        }
      />
    </div>
  ),
};

export const NotFound: Story = {
  render: () => (
    <div className="w-[420px]">
      <NotFoundState
        resourceLabel="run"
        action={
          <Button size="sm" variant="secondary">
            Back to list
          </Button>
        }
      />
    </div>
  ),
};

export const ComingSoon: Story = {
  render: () => (
    <div className="w-[420px]">
      <ComingSoonState featureLabel="Comparisons" />
    </div>
  ),
};

export const PermissionDenied: Story = {
  render: () => (
    <div className="w-[420px]">
      <PermissionDeniedState
        action={
          <Button size="sm" variant="secondary">
            Switch project
          </Button>
        }
      />
    </div>
  ),
};

export const Success: Story = {
  render: () => (
    <div className="w-[420px]">
      <SuccessState
        title="Invitation sent"
        description="They’ll get an email with access instructions. You can keep working in the meantime."
        action={
          <Button size="sm" variant="primary">
            Done
          </Button>
        }
      />
    </div>
  ),
};
