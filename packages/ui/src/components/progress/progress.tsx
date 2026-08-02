"use client";

import * as ProgressPrimitive from "@radix-ui/react-progress";

import { cn } from "../../lib/cn";

import type { ComponentPropsWithoutRef } from "react";

export type ProgressProps = ComponentPropsWithoutRef<typeof ProgressPrimitive.Root> & {
  value?: number;
};

export function Progress({ className, value = 0, ...props }: ProgressProps) {
  const clamped = Math.max(0, Math.min(100, value));
  return (
    <ProgressPrimitive.Root
      value={clamped}
      className={cn("relative h-1.5 w-full overflow-hidden rounded-full bg-muted", className)}
      {...props}
    >
      <ProgressPrimitive.Indicator
        className="h-full w-full flex-1 bg-accent transition-transform duration-[var(--ef-duration-normal)] ease-[var(--ef-ease-standard)]"
        style={{ transform: `translateX(-${String(100 - clamped)}%)` }}
      />
    </ProgressPrimitive.Root>
  );
}
