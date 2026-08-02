"use client";

import { toast } from "@agent-eval/ui";
import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

import { caseQueryKey, casesQueryKey } from "./utils";

import { ConfirmationDialog } from "@/components/patterns/confirmation-dialog";
import { deprecateCase } from "@/lib/api/cases";
import { ApiError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/auth-provider";

export interface DeprecateCaseDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  caseId: string;
  projectId: string;
  caseName: string;
  onDeprecated?: () => void;
}

export function DeprecateCaseDialog({
  open,
  onOpenChange,
  caseId,
  projectId,
  caseName,
  onDeprecated,
}: DeprecateCaseDialogProps) {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const router = useRouter();

  return (
    <ConfirmationDialog
      open={open}
      onOpenChange={onOpenChange}
      variant="destructive"
      title="Deprecate case?"
      description={
        <>
          <span className="font-medium text-foreground">{caseName}</span> will be marked deprecated.
          Existing versions remain available for historical runs, but new drafts are blocked.
        </>
      }
      confirmLabel="Deprecate case"
      onConfirm={async () => {
        if (!token) {
          throw new Error("Missing auth token");
        }
        try {
          await deprecateCase(token, caseId);
          await Promise.all([
            queryClient.invalidateQueries({ queryKey: casesQueryKey(projectId) }),
            queryClient.invalidateQueries({ queryKey: caseQueryKey(caseId) }),
          ]);
          toast.success("Case deprecated", { description: caseName });
          onDeprecated?.();
          router.refresh();
        } catch (cause) {
          const message =
            cause instanceof ApiError
              ? cause.message
              : "Could not deprecate the case. Please try again.";
          toast.error("Deprecate failed", { description: message });
          throw cause;
        }
      }}
    />
  );
}
