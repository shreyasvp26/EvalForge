import { cn } from "@agent-eval/ui";

import type { HTMLAttributes, ReactNode } from "react";

/**
 * Page content widths — Overview (`full`) is the golden reference for
 * list/dashboard canvases. Narrower widths are for forms and settings.
 */
const widthMap = {
  sm: "max-w-2xl",
  md: "max-w-3xl",
  lg: "max-w-5xl",
  xl: "max-w-6xl",
  /** Product canvas: centered max-w-7xl with shared shell padding (Overview). */
  full: "max-w-7xl",
} as const;

export type PageLayoutProps = HTMLAttributes<HTMLDivElement> & {
  children: ReactNode;
  /**
   * Content max width. Default `xl` for detail/forms.
   * Use `full` for Overview and data-table list pages (shared product canvas).
   * Use `lg` for Settings and other intentionally narrower readable columns.
   */
  width?: keyof typeof widthMap;
  /** Flush to shell edges (no horizontal padding). Useful inside SplitView panes. */
  flush?: boolean;
};

/**
 * Canonical page canvas. Every product route should wrap content in PageLayout.
 *
 * Geometry (aligned to Overview):
 * - max-width from `width`
 * - horizontal centering via `mx-auto`
 * - responsive horizontal padding
 * - consistent vertical padding
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
        flush ? "px-0 py-0" : "px-4 py-5 sm:px-6 sm:py-6",
        className,
      )}
      data-page-layout
      {...props}
    >
      {children}
    </div>
  );
}
