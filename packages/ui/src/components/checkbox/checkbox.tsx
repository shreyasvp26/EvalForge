"use client";

import * as CheckboxPrimitive from "@radix-ui/react-checkbox";

import { Icon } from "../../icon/icon";
import { Check } from "../../icon/icons";
import { cn } from "../../lib/cn";

import type { ComponentPropsWithoutRef } from "react";

export type CheckboxProps = ComponentPropsWithoutRef<typeof CheckboxPrimitive.Root>;

export function Checkbox({ className, disabled, ...props }: CheckboxProps) {
  return (
    <CheckboxPrimitive.Root
      disabled={disabled}
      className={cn(
        "peer h-4 w-4 shrink-0 rounded-[4px] border border-border-strong bg-input transition-[background-color,border-color] duration-[var(--ef-duration-fast)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:cursor-not-allowed disabled:opacity-50 data-[state=checked]:border-accent data-[state=checked]:bg-accent data-[state=checked]:text-accent-foreground",
        className,
      )}
      {...props}
    >
      <CheckboxPrimitive.Indicator className="flex items-center justify-center text-current">
        <Icon icon={Check} size="xs" strokeWidth={2.5} aria-hidden />
      </CheckboxPrimitive.Indicator>
    </CheckboxPrimitive.Root>
  );
}
