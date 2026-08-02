"use client";

import * as LabelPrimitive from "@radix-ui/react-label";

import { cn } from "../../lib/cn";

import type { ComponentPropsWithoutRef } from "react";

export type LabelProps = ComponentPropsWithoutRef<typeof LabelPrimitive.Root>;

export function Label({ className, ...props }: LabelProps) {
  return (
    <LabelPrimitive.Root
      className={cn(
        "text-[length:var(--ef-text-caption)] leading-[var(--ef-text-caption-leading)] font-medium text-foreground peer-disabled:cursor-not-allowed peer-disabled:opacity-50",
        className,
      )}
      {...props}
    />
  );
}
