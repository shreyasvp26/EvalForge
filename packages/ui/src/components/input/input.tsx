import { cn } from "../../lib/cn";

import type { InputHTMLAttributes } from "react";

export type InputProps = InputHTMLAttributes<HTMLInputElement>;

export function Input({ className, type = "text", disabled, ...props }: InputProps) {
  return (
    <input
      type={type}
      disabled={disabled}
      className={cn(
        "flex h-9 w-full rounded-[var(--ef-radius-control)] border border-border bg-input pl-3 pr-3 text-[length:var(--ef-text-body)] leading-[var(--ef-text-body-leading)] text-input-foreground placeholder:text-muted-foreground transition-[border-color,box-shadow] duration-[var(--ef-duration-fast)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      {...props}
    />
  );
}
