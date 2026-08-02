"use client";

import { InspectorLayout, cn } from "@agent-eval/ui";

import type { ReactNode } from "react";

export interface DetailLayoutProps {
  /** Primary detail canvas (header + body). */
  children: ReactNode;
  /** Optional right inspector (metadata, scores, activity). */
  inspector?: ReactNode;
  inspectorOpen?: boolean;
  inspectorWidth?: number;
  className?: string;
}

/**
 * Detail page layout with an opt-in inspector pane.
 * Prefer this over putting permanent inspector chrome in the app shell.
 */
export function DetailLayout({
  children,
  inspector,
  inspectorOpen = true,
  inspectorWidth = 360,
  className,
}: DetailLayoutProps) {
  return (
    <InspectorLayout
      className={cn("min-h-full", className)}
      main={<div className="min-h-full px-4 py-8 sm:px-6">{children}</div>}
      defaultWidth={inspectorWidth}
      open={inspectorOpen}
      {...(inspector !== undefined ? { inspector } : {})}
    />
  );
}
