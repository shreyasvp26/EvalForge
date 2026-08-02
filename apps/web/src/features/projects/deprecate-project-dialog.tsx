"use client";

import { toast } from "@agent-eval/ui";
import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

import { projectQueryKey, projectsQueryKey } from "./utils";

import { ConfirmationDialog } from "@/components/patterns/confirmation-dialog";
import { ApiError } from "@/lib/api/client";
import { deprecateProject } from "@/lib/api/projects";
import { useAuth } from "@/lib/auth/auth-provider";

export interface DeprecateProjectDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectId: string;
  projectName: string;
  onDeprecated?: () => void;
}

export function DeprecateProjectDialog({
  open,
  onOpenChange,
  projectId,
  projectName,
  onDeprecated,
}: DeprecateProjectDialogProps) {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const router = useRouter();

  return (
    <ConfirmationDialog
      open={open}
      onOpenChange={onOpenChange}
      variant="destructive"
      title="Deprecate project?"
      description={
        <>
          <span className="font-medium text-foreground">{projectName}</span> will be marked
          deprecated. Existing runs remain available, but the project should no longer be used for
          new evaluation work.
        </>
      }
      confirmLabel="Deprecate project"
      onConfirm={async () => {
        if (!token) {
          throw new Error("Missing auth token");
        }
        try {
          await deprecateProject(token, projectId);
          await Promise.all([
            queryClient.invalidateQueries({ queryKey: projectsQueryKey }),
            queryClient.invalidateQueries({ queryKey: projectQueryKey(projectId) }),
          ]);
          toast.success("Project deprecated", { description: projectName });
          onDeprecated?.();
          router.refresh();
        } catch (cause) {
          const message =
            cause instanceof ApiError
              ? cause.message
              : "Could not deprecate the project. Please try again.";
          toast.error("Deprecate failed", { description: message });
          throw cause;
        }
      }}
    />
  );
}
