"use client";

import { useCallback, useEffect, useId, useRef, useState } from "react";

import { cn } from "../../lib/cn";

import type { CSSProperties, HTMLAttributes, ReactNode } from "react";

export type InspectorLayoutProps = HTMLAttributes<HTMLDivElement> & {
  main: ReactNode;
  inspector?: ReactNode;
  /** Default inspector width in pixels. */
  defaultWidth?: number;
  minWidth?: number;
  maxWidth?: number;
  open?: boolean;
};

/**
 * Opt-in main + right inspector split. Not permanent chrome —
 * pages choose when to show the inspector.
 */
export function InspectorLayout({
  main,
  inspector,
  defaultWidth = 360,
  minWidth = 280,
  maxWidth = 560,
  open = true,
  className,
  ...props
}: InspectorLayoutProps) {
  const [width, setWidth] = useState(defaultWidth);
  const dragging = useRef(false);
  const labelId = useId();

  const onPointerMove = useCallback(
    (event: PointerEvent) => {
      if (!dragging.current) return;
      const next = window.innerWidth - event.clientX;
      setWidth(Math.min(maxWidth, Math.max(minWidth, next)));
    },
    [maxWidth, minWidth],
  );

  const stopDragging = useCallback(() => {
    dragging.current = false;
    document.body.style.cursor = "";
    document.body.style.userSelect = "";
  }, []);

  useEffect(() => {
    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", stopDragging);
    return () => {
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", stopDragging);
    };
  }, [onPointerMove, stopDragging]);

  const showInspector = open && inspector !== undefined && inspector !== null;

  return (
    <div className={cn("flex min-h-0 min-w-0 flex-1", className)} {...props}>
      <div className="min-w-0 flex-1 overflow-auto">{main}</div>
      {showInspector ? (
        <>
          <div
            role="separator"
            aria-orientation="vertical"
            aria-labelledby={labelId}
            tabIndex={0}
            className="group relative hidden w-px shrink-0 cursor-col-resize bg-border focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring md:block"
            onPointerDown={() => {
              dragging.current = true;
              document.body.style.cursor = "col-resize";
              document.body.style.userSelect = "none";
            }}
            onKeyDown={(event) => {
              if (event.key === "ArrowLeft") {
                event.preventDefault();
                setWidth((w) => Math.min(maxWidth, w + 16));
              }
              if (event.key === "ArrowRight") {
                event.preventDefault();
                setWidth((w) => Math.max(minWidth, w - 16));
              }
            }}
          >
            <span id={labelId} className="sr-only">
              Resize inspector
            </span>
            <span className="absolute inset-y-0 -left-1 -right-1" aria-hidden />
          </div>
          <aside
            className="w-full shrink-0 overflow-auto border-t border-border bg-card md:w-[var(--ef-inspector-width)] md:border-l md:border-t-0"
            style={{ "--ef-inspector-width": `${String(width)}px` } as CSSProperties}
          >
            {inspector}
          </aside>
        </>
      ) : null}
    </div>
  );
}
