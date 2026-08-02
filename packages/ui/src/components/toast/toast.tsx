"use client";

import { Toaster as SonnerToaster, toast } from "sonner";

import type { CSSProperties } from "react";

export function Toaster() {
  return (
    <SonnerToaster
      theme="system"
      className="toaster group"
      position="bottom-right"
      toastOptions={{
        classNames: {
          toast:
            "group toast border border-border bg-card text-card-foreground shadow-ef-md rounded-[var(--ef-radius-panel)]",
          title: "text-[length:var(--ef-text-body)] font-medium",
          description: "text-[length:var(--ef-text-caption)] text-muted-foreground",
          actionButton: "bg-accent text-accent-foreground",
          cancelButton: "bg-muted text-foreground",
        },
        style: {
          "--normal-bg": "var(--ef-card)",
          "--normal-border": "var(--ef-border)",
          "--normal-text": "var(--ef-card-foreground)",
        } as CSSProperties,
      }}
    />
  );
}

export { toast };
