import { cn } from "../lib/cn";

import type { LucideIcon, LucideProps } from "lucide-react";

const sizeMap = {
  xs: 12,
  sm: 14,
  md: 16,
  lg: 18,
  xl: 20,
} as const;

export type IconSize = keyof typeof sizeMap;

export type IconProps = Omit<LucideProps, "ref" | "size"> & {
  icon: LucideIcon;
  size?: IconSize;
  /** Decorative by default; set aria-label for meaningful icons. */
  "aria-label"?: string;
};

/**
 * Canonical icon wrapper. Apps must import icons from `@agent-eval/ui`,
 * never from `lucide-react` directly.
 */
export function Icon({
  icon: Comp,
  size = "md",
  className,
  strokeWidth = 1.75,
  "aria-label": ariaLabel,
  "aria-hidden": ariaHidden,
  ...props
}: IconProps) {
  const decorative = ariaLabel === undefined;
  return (
    <Comp
      size={sizeMap[size]}
      strokeWidth={strokeWidth}
      className={cn("shrink-0", className)}
      aria-label={ariaLabel}
      aria-hidden={ariaHidden ?? decorative}
      {...props}
    />
  );
}
