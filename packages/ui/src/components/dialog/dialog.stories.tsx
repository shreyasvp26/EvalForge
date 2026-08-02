"use client";

import { Button } from "../button/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "./dialog";

import type { Meta, StoryObj } from "@storybook/react";

function Demo() {
  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="outline">Open dialog</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Cancel run?</DialogTitle>
          <DialogDescription>
            This stops the in-flight evaluation. Partial events already captured remain immutable.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="ghost">Keep running</Button>
          <Button variant="danger">Cancel run</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

const meta = {
  title: "Overlays/Dialog",
  component: Demo,
} satisfies Meta<typeof Demo>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
