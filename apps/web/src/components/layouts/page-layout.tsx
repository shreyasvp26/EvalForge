import { cn } from "@agent-eval/ui";

import type { HTMLAttributes, ReactNode } from "react";

const widthMap = {
  sm: "max-w-2xl",
  md: "max-w-3xl",
  lg: "max-w-5xl",
  xl: "max-w-6xl",
  full: "max-w-none",
} as const;

export type PageLayoutProps = HTMLAttributes<HTMLDivElement> & {
  children: ReactNode;
  /** Content max width. Default `xl`. Use `full` for tables and dense lists. */
  width?: keyof typeof widthMap;
  /** Flush to shell edges (no horizontal padding). Useful inside SplitView panes. */
  flush?: boolean;
};

/**
 * Canonical page canvas. Every product route should wrap content in PageLayout.
 */
export function PageLayout({
  children,
  width = "xl",
  flush = false,
  className,
  ...props
}: PageLayoutProps) {
  return (
    <div
      className={cn(
        "mx-auto w-full",
        widthMap[width],
        flush ? "px-0 py-0" : "px-4 py-8 sm:px-6",
        className,
      )}
      data-page-layout
      {...props}
    >
      {children}
    </div>
  );
}
