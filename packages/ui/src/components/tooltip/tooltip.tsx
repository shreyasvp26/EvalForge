"use client";

import * as TooltipPrimitive from "@radix-ui/react-tooltip";

import { cn } from "../../lib/cn";

import type { ComponentPropsWithoutRef, ReactNode } from "react";

export const TooltipProvider = TooltipPrimitive.Provider;
export const Tooltip = TooltipPrimitive.Root;
export const TooltipTrigger = TooltipPrimitive.Trigger;

export function TooltipContent({
  className,
  sideOffset = 6,
  ...props
}: ComponentPropsWithoutRef<typeof TooltipPrimitive.Content>) {
  return (
    <TooltipPrimitive.Portal>
      <TooltipPrimitive.Content
        sideOffset={sideOffset}
        className={cn(
          "z-[var(--ef-z-dropdown)] max-w-xs rounded-[var(--ef-radius-control)] border border-border bg-popover px-2 py-1 text-[length:var(--ef-text-caption)] leading-[var(--ef-text-caption-leading)] text-popover-foreground shadow-ef-sm",
          className,
        )}
        {...props}
      />
    </TooltipPrimitive.Portal>
  );
}

export function SimpleTooltip({ content, children }: { content: ReactNode; children: ReactNode }) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>{children}</TooltipTrigger>
      <TooltipContent>{content}</TooltipContent>
    </Tooltip>
  );
}
