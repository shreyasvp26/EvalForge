"use client";

import { Dialog, DialogContent, DialogDescription, DialogTitleHidden } from "@agent-eval/ui";
import { useEffect, useRef } from "react";

import type { SectionOpenState } from "@/components/shell/use-ui-preferences";

import { Sidebar } from "@/components/shell/sidebar";

export interface MobileNavDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  sectionOpen: SectionOpenState;
  onToggleSection: (id: string) => void;
}

/**
 * Mobile/tablet overlay navigation with Radix focus trap + restore.
 */
export function MobileNavDrawer({
  open,
  onOpenChange,
  sectionOpen,
  onToggleSection,
}: MobileNavDrawerProps) {
  const triggerRef = useRef<Element | null>(null);

  useEffect(() => {
    if (open) {
      triggerRef.current = document.activeElement;
    }
  }, [open]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        showClose={false}
        className="fixed top-0 left-0 h-dvh w-[min(100%,16rem)] max-w-none translate-x-0 translate-y-0 rounded-none border-y-0 border-l-0 p-0 sm:max-w-none"
        onCloseAutoFocus={(event) => {
          event.preventDefault();
          if (triggerRef.current instanceof HTMLElement) {
            triggerRef.current.focus();
          }
        }}
      >
        <DialogTitleHidden>Navigation</DialogTitleHidden>
        <DialogDescription className="sr-only">Primary application navigation</DialogDescription>
        <Sidebar
          collapsed={false}
          showCollapseControl={false}
          sectionOpen={sectionOpen}
          onToggleSection={onToggleSection}
          onNavigate={() => {
            onOpenChange(false);
          }}
          className="h-full w-full border-0"
        />
      </DialogContent>
    </Dialog>
  );
}
