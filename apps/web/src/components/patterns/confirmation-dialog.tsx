"use client";

import {
  AlertTriangle,
  Button,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Icon,
  ShieldAlert,
  cn,
} from "@agent-eval/ui";
import { useState } from "react";

import type { LucideIcon } from "@agent-eval/ui";
import type { ReactNode } from "react";

export interface ConfirmationDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: ReactNode;
  /** Confirm button label. */
  confirmLabel?: string;
  cancelLabel?: string;
  /** `destructive` styles the confirm action as danger and defaults the icon. */
  variant?: "default" | "destructive";
  icon?: LucideIcon;
  /** Called on confirm. May return a Promise — dialog shows loading until settled. */
  onConfirm: () => void | Promise<void>;
  /** When true, ignore outside dismiss while confirming. */
  disableOutsideCloseWhileLoading?: boolean;
}

/**
 * Standard product confirmation. Supports async confirm, destructive styling,
 * focus trap (Radix), Escape, and loading on the primary action.
 */
export function ConfirmationDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  variant = "default",
  icon,
  onConfirm,
  disableOutsideCloseWhileLoading = true,
}: ConfirmationDialogProps) {
  const [loading, setLoading] = useState(false);
  const resolvedIcon = icon ?? (variant === "destructive" ? ShieldAlert : AlertTriangle);

  const handleConfirm = async () => {
    setLoading(true);
    try {
      await onConfirm();
      onOpenChange(false);
    } catch {
      // Caller owns toast/error presentation; keep dialog open for retry.
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (loading && disableOutsideCloseWhileLoading) return;
        onOpenChange(next);
      }}
    >
      <DialogContent
        showClose={!loading}
        className="sm:max-w-md"
        onPointerDownOutside={(event) => {
          if (loading && disableOutsideCloseWhileLoading) event.preventDefault();
        }}
        onEscapeKeyDown={(event) => {
          if (loading && disableOutsideCloseWhileLoading) event.preventDefault();
        }}
      >
        <DialogHeader>
          <div className="flex items-start gap-3">
            <div
              className={cn(
                "mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-[var(--ef-radius-control)]",
                variant === "destructive"
                  ? "bg-danger-muted text-danger"
                  : "bg-muted text-foreground",
              )}
            >
              <Icon icon={resolvedIcon} size="md" aria-hidden />
            </div>
            <div className="min-w-0 space-y-1">
              <DialogTitle>{title}</DialogTitle>
              <DialogDescription>{description}</DialogDescription>
            </div>
          </div>
        </DialogHeader>
        <DialogFooter>
          <Button
            type="button"
            variant="ghost"
            disabled={loading}
            onClick={() => {
              onOpenChange(false);
            }}
          >
            {cancelLabel}
          </Button>
          <Button
            type="button"
            variant={variant === "destructive" ? "danger" : "primary"}
            loading={loading}
            onClick={() => {
              void handleConfirm();
            }}
          >
            {confirmLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
