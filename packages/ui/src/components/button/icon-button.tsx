import { Icon } from "../../icon/icon";
import { cn } from "../../lib/cn";

import type { IconSize } from "../../icon/icon";
import type { LucideIcon } from "lucide-react";
import type { ButtonHTMLAttributes } from "react";

const sizeClass = {
  sm: "h-8 w-8",
  md: "h-9 w-9",
  lg: "h-10 w-10",
} as const;

const iconSize: Record<keyof typeof sizeClass, IconSize> = {
  sm: "sm",
  md: "md",
  lg: "md",
};

export type IconButtonProps = Omit<ButtonHTMLAttributes<HTMLButtonElement>, "children"> & {
  icon: LucideIcon;
  label: string;
  size?: keyof typeof sizeClass;
  variant?: "ghost" | "outline" | "secondary";
};

export function IconButton({
  icon,
  label,
  size = "md",
  variant = "ghost",
  className,
  disabled,
  ...props
}: IconButtonProps) {
  return (
    <button
      type="button"
      aria-label={label}
      disabled={disabled}
      className={cn(
        "inline-flex items-center justify-center rounded-[var(--ef-radius-control)] text-foreground transition-[background-color,opacity] duration-[var(--ef-duration-fast)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-50",
        sizeClass[size],
        variant === "ghost" && "hover:bg-muted",
        variant === "outline" && "border border-border hover:bg-muted",
        variant === "secondary" && "bg-muted hover:bg-border",
        className,
      )}
      {...props}
    >
      <Icon icon={icon} size={iconSize[size]} aria-hidden />
    </button>
  );
}
