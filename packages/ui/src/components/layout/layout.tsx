import { cn } from "../../lib/cn";

import type { HTMLAttributes } from "react";

const gapMap = {
  1: "gap-1",
  2: "gap-2",
  3: "gap-3",
  4: "gap-4",
  5: "gap-6",
  6: "gap-8",
  7: "gap-12",
  8: "gap-16",
} as const;

export type StackProps = HTMLAttributes<HTMLDivElement> & {
  gap?: keyof typeof gapMap;
};

/** Vertical stack using the spacing scale. */
export function Stack({ className, gap = 4, ...props }: StackProps) {
  return <div className={cn("flex flex-col", gapMap[gap], className)} {...props} />;
}

export type ClusterProps = HTMLAttributes<HTMLDivElement> & {
  gap?: keyof typeof gapMap;
};

/** Horizontal wrapping cluster. */
export function Cluster({ className, gap = 2, ...props }: ClusterProps) {
  return <div className={cn("flex flex-wrap items-center", gapMap[gap], className)} {...props} />;
}

export type ContainerProps = HTMLAttributes<HTMLDivElement> & {
  width?: "sm" | "md" | "lg" | "xl" | "full";
};

const widthMap = {
  sm: "max-w-2xl",
  md: "max-w-3xl",
  lg: "max-w-5xl",
  xl: "max-w-6xl",
  full: "max-w-none",
} as const;

export function Container({ className, width = "xl", ...props }: ContainerProps) {
  return (
    <div className={cn("mx-auto w-full px-4 sm:px-6", widthMap[width], className)} {...props} />
  );
}

export type PanelProps = HTMLAttributes<HTMLDivElement>;

export function Panel({ className, ...props }: PanelProps) {
  return (
    <div
      className={cn(
        "rounded-[var(--ef-radius-panel)] border border-border bg-card text-card-foreground",
        className,
      )}
      {...props}
    />
  );
}
