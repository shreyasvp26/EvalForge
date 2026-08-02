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

import { adapterQueryKey, agentQueryKey } from "./utils";

import { InlineError } from "@/components/patterns/inline-error";
import { createAdapterDraftVersion } from "@/lib/api/agents";
import { ApiError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/auth-provider";

const schema = z.object({
  label: z.string().trim().min(1, "Label is required").max(200, "Label is too long"),
  notes: z.string().max(5000, "Notes are too long"),
});

export interface CreateAdapterDraftDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  adapterId: string;
  agentId: string;
}

export function CreateAdapterDraftDialog({
  open,
  onOpenChange,
  adapterId,
  agentId,
}: CreateAdapterDraftDialogProps) {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const labelId = useId();
  const notesId = useId();

  const [label, setLabel] = useState("");
  const [notes, setNotes] = useState("");
  const [fieldErrors, setFieldErrors] = useState<{ label?: string; notes?: string }>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function reset() {
    setLabel("");
    setNotes("");
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

    const parsed = schema.safeParse({ label, notes });
    if (!parsed.success) {
      const nextErrors: { label?: string; notes?: string } = {};
      for (const issue of parsed.error.issues) {
        const key = issue.path[0];
        if (key === "label" || key === "notes") {
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
        const version = await createAdapterDraftVersion(token, adapterId, {
          label: parsed.data.label,
          notes: parsed.data.notes,
        });
        await Promise.all([
          queryClient.invalidateQueries({ queryKey: adapterQueryKey(adapterId) }),
          queryClient.invalidateQueries({ queryKey: agentQueryKey(agentId) }),
        ]);
        toast.success("Adapter draft created", {
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
          <DialogTitle>Create adapter draft</DialogTitle>
          <DialogDescription>
            Add a draft adapter mapping release. Publish when it is ready to pair with agent
            versions on runs.
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
              placeholder="e.g. stream-json-v2"
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
            <Label htmlFor={notesId}>Notes</Label>
            <Textarea
              id={notesId}
              value={notes}
              disabled={submitting}
              rows={4}
              placeholder="Optional notes for this adapter release"
              onChange={(event) => {
                setNotes(event.target.value);
                if (fieldErrors.notes) {
                  setFieldErrors((current) => {
                    const { notes: _removed, ...rest } = current;
                    return rest;
                  });
                }
              }}
              aria-invalid={fieldErrors.notes ? true : undefined}
            />
            {fieldErrors.notes ? <InlineError>{fieldErrors.notes}</InlineError> : null}
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
