"use client";

import { Button, Input, Label, Stack } from "@agent-eval/ui";
import { useState } from "react";

import { ConfirmationDialog } from "./confirmation-dialog";
import { ErrorBoundary } from "./error-boundary";
import { InlineError } from "./inline-error";

import type { Meta, StoryObj } from "@storybook/react";

const meta = {
  title: "Product Patterns/Feedback",
  parameters: { layout: "padded" },
} satisfies Meta;

export default meta;
type Story = StoryObj;

export const InlineFieldError: Story = {
  render: () => (
    <Stack gap={2} className="w-[320px]">
      <Label htmlFor="name">Name</Label>
      <Input id="name" aria-invalid defaultValue="" placeholder="Required" />
      <InlineError>Enter a name to continue.</InlineError>
    </Stack>
  ),
};

export const InlineBlockError: Story = {
  render: () => (
    <div className="w-[420px]">
      <InlineError density="block" title="Couldn’t save changes">
        The server rejected the request. Check your connection and try again.
      </InlineError>
    </div>
  ),
};

function ConfirmationDemo({ variant }: { variant: "default" | "destructive" }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button
        variant={variant === "destructive" ? "danger" : "primary"}
        onClick={() => {
          setOpen(true);
        }}
      >
        {variant === "destructive" ? "Delete item" : "Archive item"}
      </Button>
      <ConfirmationDialog
        open={open}
        onOpenChange={setOpen}
        variant={variant}
        title={variant === "destructive" ? "Delete this item?" : "Archive this item?"}
        description={
          variant === "destructive"
            ? "This can’t be undone. Related history stays immutable, but the item will no longer appear in lists."
            : "You can restore it later from archived items."
        }
        confirmLabel={variant === "destructive" ? "Delete" : "Archive"}
        onConfirm={async () => {
          await new Promise((resolve) => {
            setTimeout(resolve, 600);
          });
        }}
      />
    </>
  );
}

export const ConfirmStandard: Story = {
  render: () => <ConfirmationDemo variant="default" />,
};

export const ConfirmDestructive: Story = {
  render: () => <ConfirmationDemo variant="destructive" />,
};

function Boom(): React.ReactNode {
  throw new Error("Demo render failure");
}

export const Boundary: Story = {
  render: () => (
    <div className="w-[420px]">
      <ErrorBoundary>
        <Boom />
      </ErrorBoundary>
    </div>
  ),
};
