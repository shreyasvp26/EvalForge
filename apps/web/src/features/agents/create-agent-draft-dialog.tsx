"use client";

import {
  Button,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Input,
  Label,
  Textarea,
  toast,
} from "@agent-eval/ui";
import { useQueryClient } from "@tanstack/react-query";
import { useId, useState } from "react";
import { z } from "zod";

import { agentQueryKey, agentsQueryKey } from "./utils";

import { InlineError } from "@/components/patterns/inline-error";
import { createAgentDraftVersion } from "@/lib/api/agents";
import { ApiError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/auth-provider";

const schema = z.object({
  label: z.string().trim().min(1, "Label is required").max(200, "Label is too long"),
  release_notes: z.string().max(5000, "Release notes are too long"),
});

export interface CreateAgentDraftDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  agentId: string;
}

export function CreateAgentDraftDialog({
  open,
  onOpenChange,
  agentId,
}: CreateAgentDraftDialogProps) {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const labelId = useId();
  const notesId = useId();

  const [label, setLabel] = useState("");
  const [releaseNotes, setReleaseNotes] = useState("");
  const [fieldErrors, setFieldErrors] = useState<{ label?: string; release_notes?: string }>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function reset() {
    setLabel("");
    setReleaseNotes("");
    setFieldErrors({});
    setFormError(null);
    setSubmitting(false);
  }

  function handleOpenChange(next: boolean) {
    if (submitting) return;
    if (!next) reset();
    onOpenChange(next);
  }

  function onSubmit(event: React.SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);

    const parsed = schema.safeParse({ label, release_notes: releaseNotes });
    if (!parsed.success) {
      const nextErrors: { label?: string; release_notes?: string } = {};
      for (const issue of parsed.error.issues) {
        const key = issue.path[0];
        if (key === "label" || key === "release_notes") {
          nextErrors[key] = issue.message;
        }
      }
      setFieldErrors(nextErrors);
      return;
    }

    if (!token) {
      setFormError("You must be signed in to create a draft.");
      return;
    }

    setFieldErrors({});
    setSubmitting(true);

    void (async () => {
      try {
        const version = await createAgentDraftVersion(token, agentId, {
          label: parsed.data.label,
          release_notes: parsed.data.release_notes,
        });
        await Promise.all([
          queryClient.invalidateQueries({ queryKey: agentQueryKey(agentId) }),
          queryClient.invalidateQueries({ queryKey: agentsQueryKey }),
        ]);
        toast.success("Agent draft created", {
          description: `v${String(version.version_number)} · ${version.label}`,
        });
        reset();
        onOpenChange(false);
      } catch (cause) {
        if (cause instanceof ApiError) {
          setFormError(cause.message);
        } else {
          setFormError("Could not create the draft. Please try again.");
        }
      } finally {
        setSubmitting(false);
      }
    })();
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent
        className="sm:max-w-md"
        showClose={!submitting}
        onPointerDownOutside={(event) => {
          if (submitting) event.preventDefault();
        }}
        onEscapeKeyDown={(event) => {
          if (submitting) event.preventDefault();
        }}
      >
        <DialogHeader>
          <DialogTitle>Create agent draft</DialogTitle>
          <DialogDescription>
            Add a draft release of this agent. Publish when it is ready to be targeted by runs.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={onSubmit} className="space-y-4" noValidate>
          {formError ? <InlineError density="block">{formError}</InlineError> : null}

          <div className="space-y-1.5">
            <Label htmlFor={labelId}>Label</Label>
            <Input
              id={labelId}
              value={label}
              autoFocus
              disabled={submitting}
              placeholder="e.g. 2026.08"
              onChange={(event) => {
                setLabel(event.target.value);
                if (fieldErrors.label) {
                  setFieldErrors((current) => {
                    const { label: _removed, ...rest } = current;
                    return rest;
                  });
                }
              }}
              aria-invalid={fieldErrors.label ? true : undefined}
            />
            {fieldErrors.label ? <InlineError>{fieldErrors.label}</InlineError> : null}
          </div>

          <div className="space-y-1.5">
            <Label htmlFor={notesId}>Release notes</Label>
            <Textarea
              id={notesId}
              value={releaseNotes}
              disabled={submitting}
              rows={4}
              placeholder="Optional notes for this release"
              onChange={(event) => {
                setReleaseNotes(event.target.value);
                if (fieldErrors.release_notes) {
                  setFieldErrors((current) => {
                    const { release_notes: _removed, ...rest } = current;
                    return rest;
                  });
                }
              }}
              aria-invalid={fieldErrors.release_notes ? true : undefined}
            />
            {fieldErrors.release_notes ? (
              <InlineError>{fieldErrors.release_notes}</InlineError>
            ) : null}
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="ghost"
              disabled={submitting}
              onClick={() => {
                handleOpenChange(false);
              }}
            >
              Cancel
            </Button>
            <Button type="submit" loading={submitting}>
              Create draft
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
