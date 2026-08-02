import { cn } from "../../lib/cn";

import type { TextareaHTMLAttributes } from "react";

export type TextareaProps = TextareaHTMLAttributes<HTMLTextAreaElement>;

export function Textarea({ className, disabled, ...props }: TextareaProps) {
  return (
    <textarea
      disabled={disabled}
      className={cn(
        "flex min-h-24 w-full rounded-[var(--ef-radius-control)] border border-border bg-input px-3 py-2 text-[length:var(--ef-text-body)] leading-[var(--ef-text-body-leading)] text-input-foreground placeholder:text-muted-foreground transition-[border-color,box-shadow] duration-[var(--ef-duration-fast)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      {...props}
    />
  );
}
