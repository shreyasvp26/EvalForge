"use client";

import {
  Button,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  Text,
} from "@agent-eval/ui";

const shortcuts = [
  { keys: "⌘K / Ctrl+K", action: "Open command palette" },
  { keys: "G then H", action: "Go to Overview" },
  { keys: "G then P", action: "Go to Projects" },
  { keys: "G then R", action: "Go to Runs" },
  { keys: "G then A", action: "Go to Agents" },
  { keys: "G then G", action: "Go to Graders" },
  { keys: "?", action: "Show keyboard shortcuts" },
  { keys: "Esc", action: "Close overlays / drawers" },
] as const;

export interface KeyboardShortcutsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function KeyboardShortcutsDialog({ open, onOpenChange }: KeyboardShortcutsDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md" showClose>
        <DialogHeader>
          <DialogTitle>Keyboard shortcuts</DialogTitle>
          <DialogDescription>
            Navigate EvalForge without leaving the keyboard. Shortcuts are ignored while typing in
            inputs.
          </DialogDescription>
        </DialogHeader>
        <ul className="space-y-2">
          {shortcuts.map((item) => (
            <li
              key={item.keys}
              className="flex items-center justify-between gap-4 rounded-[var(--ef-radius-control)] border border-border px-3 py-2"
            >
              <Text variant="body">{item.action}</Text>
              <kbd className="shrink-0 rounded border border-border bg-muted px-2 py-0.5 font-mono text-[length:var(--ef-text-caption)] text-muted-foreground">
                {item.keys}
              </kbd>
            </li>
          ))}
        </ul>
        <div className="flex justify-end">
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => {
              onOpenChange(false);
            }}
          >
            Close
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
