"use client";

import * as DialogPrimitive from "@radix-ui/react-dialog";
import { VisuallyHidden } from "@radix-ui/react-visually-hidden";

import { Icon } from "../../icon/icon";
import { X } from "../../icon/icons";
import { cn } from "../../lib/cn";
import { Heading } from "../../typography/heading";
import { Text } from "../../typography/text";

import type { ComponentPropsWithoutRef, HTMLAttributes, ReactNode } from "react";

export const Dialog = DialogPrimitive.Root;
export const DialogTrigger = DialogPrimitive.Trigger;
export const DialogClose = DialogPrimitive.Close;
export const DialogPortal = DialogPrimitive.Portal;

export function DialogOverlay({
  className,
  ...props
}: ComponentPropsWithoutRef<typeof DialogPrimitive.Overlay>) {
  return (
    <DialogPrimitive.Overlay
      className={cn("fixed inset-0 z-[var(--ef-z-overlay)] bg-foreground/40", className)}
      {...props}
    />
  );
}

export type DialogContentProps = ComponentPropsWithoutRef<typeof DialogPrimitive.Content> & {
  showClose?: boolean;
  overlayClassName?: string;
};

export function DialogContent({
  className,
  children,
  showClose = true,
  overlayClassName,
  ...props
}: DialogContentProps) {
  return (
    <DialogPortal>
      <DialogOverlay className={overlayClassName} />
      <DialogPrimitive.Content
        className={cn(
          "fixed left-1/2 top-1/2 z-[var(--ef-z-modal)] grid w-[calc(100%-2rem)] max-h-[min(90dvh,56rem)] max-w-lg -translate-x-1/2 -translate-y-1/2 gap-4 overflow-y-auto rounded-[var(--ef-radius-dialog)] border border-border bg-card p-5 text-card-foreground shadow-ef-md focus:outline-none",
          className,
        )}
        {...props}
      >
        {children}
        {showClose ? (
          <DialogPrimitive.Close
            className="absolute right-3 top-3 inline-flex h-8 w-8 items-center justify-center rounded-[var(--ef-radius-control)] text-muted-foreground hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            aria-label="Close"
          >
            <Icon icon={X} size="sm" aria-hidden />
          </DialogPrimitive.Close>
        ) : null}
      </DialogPrimitive.Content>
    </DialogPortal>
  );
}

export function DialogHeader({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("flex flex-col gap-1 pr-8", className)} {...props} />;
}

export function DialogTitle({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <DialogPrimitive.Title asChild>
      <Heading variant="card" level={2} className={className}>
        {children}
      </Heading>
    </DialogPrimitive.Title>
  );
}

export function DialogDescription({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <DialogPrimitive.Description asChild>
      <Text variant="secondary" className={className}>
        {children}
      </Text>
    </DialogPrimitive.Description>
  );
}

export function DialogFooter({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("flex flex-col-reverse gap-2 sm:flex-row sm:justify-end", className)}
      {...props}
    />
  );
}

/** Use when a dialog must stay untitled visually but needs an accessible name. */
export function DialogTitleHidden({ children }: { children: ReactNode }) {
  return (
    <VisuallyHidden asChild>
      <DialogPrimitive.Title>{children}</DialogPrimitive.Title>
    </VisuallyHidden>
  );
}
