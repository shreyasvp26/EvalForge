"use client";

import { toast } from "@agent-eval/ui";
import { useQueryClient } from "@tanstack/react-query";

import { runQueryKey, runsListQueryKey, runsQueryKey } from "./utils";

import { ConfirmationDialog } from "@/components/patterns/confirmation-dialog";
import { ApiError } from "@/lib/api/client";
import { cancelRun } from "@/lib/api/runs";
import { useAuth } from "@/lib/auth/auth-provider";

export interface CancelRunDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  runId: string;
  projectId: string;
  statusLabel: string;
}

export function CancelRunDialog({
  open,
  onOpenChange,
  runId,
  projectId,
  statusLabel,
}: CancelRunDialogProps) {
  const { token } = useAuth();
  const queryClient = useQueryClient();

  return (
    <ConfirmationDialog
      open={open}
      onOpenChange={onOpenChange}
      variant="destructive"
      title="Cancel run?"
      description={
        <>
          This run is currently <span className="font-medium text-foreground">{statusLabel}</span>.
          Cancellation is cooperative and may take a moment to take effect.
        </>
      }
      confirmLabel="Cancel run"
      onConfirm={async () => {
        if (!token) throw new Error("Missing auth token");
        try {
          await cancelRun(token, runId);
          await Promise.all([
            queryClient.invalidateQueries({ queryKey: runsQueryKey }),
            queryClient.invalidateQueries({ queryKey: runsListQueryKey(projectId) }),
            queryClient.invalidateQueries({ queryKey: runQueryKey(runId) }),
          ]);
          toast.success("Run cancelled");
        } catch (cause) {
          toast.error("Cancel failed", {
            description: cause instanceof ApiError ? cause.message : "Please try again.",
          });
          throw cause;
        }
      }}
    />
  );
}
