"use client";

import { cn } from "@agent-eval/ui";
import { useCallback, useEffect, useId, useRef, useState } from "react";

import type { CSSProperties, ReactNode } from "react";

export interface SplitViewProps {
  primary: ReactNode;
  secondary: ReactNode;
  /** Show the secondary pane. Default true on `md+`; hidden on small screens unless forced. */
  secondaryOpen?: boolean;
  defaultPrimaryWidth?: number;
  minPrimaryWidth?: number;
  maxPrimaryWidth?: number;
  className?: string;
}

/**
 * List/detail (or master/secondary) split. Primary pane is resizable on desktop.
 */
export function SplitView({
  primary,
  secondary,
  secondaryOpen = true,
  defaultPrimaryWidth = 360,
  minPrimaryWidth = 280,
  maxPrimaryWidth = 520,
  className,
}: SplitViewProps) {
  const [width, setWidth] = useState(defaultPrimaryWidth);
  const dragging = useRef(false);
  const labelId = useId();

  const onPointerMove = useCallback(
    (event: PointerEvent) => {
      if (!dragging.current) return;
      setWidth(Math.min(maxPrimaryWidth, Math.max(minPrimaryWidth, event.clientX)));
    },
    [maxPrimaryWidth, minPrimaryWidth],
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

  return (
    <div className={cn("flex min-h-0 min-w-0 flex-1", className)}>
      <div
        className={cn(
          "min-h-0 w-full shrink-0 overflow-auto border-border md:border-r",
          secondaryOpen ? "md:w-[var(--ef-split-primary-width)] md:shrink-0" : "w-full",
        )}
        style={
          secondaryOpen
            ? ({ "--ef-split-primary-width": `${String(width)}px` } as CSSProperties)
            : undefined
        }
      >
        {primary}
      </div>

      {secondaryOpen ? (
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
                setWidth((w) => Math.max(minPrimaryWidth, w - 16));
              }
              if (event.key === "ArrowRight") {
                event.preventDefault();
                setWidth((w) => Math.min(maxPrimaryWidth, w + 16));
              }
            }}
          >
            <span id={labelId} className="sr-only">
              Resize primary pane
            </span>
            <span className="absolute inset-y-0 -left-1 -right-1" aria-hidden />
          </div>
          <div className="hidden min-w-0 flex-1 overflow-auto md:block">{secondary}</div>
        </>
      ) : null}
    </div>
  );
}
