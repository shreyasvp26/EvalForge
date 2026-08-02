"use client";

import {
  Button,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Label,
  Textarea,
  toast,
} from "@agent-eval/ui";
import { useQueryClient } from "@tanstack/react-query";
import { useId, useState } from "react";
import { z } from "zod";

import { caseQueryKey, casesQueryKey } from "./utils";

import { InlineError } from "@/components/patterns/inline-error";
import { createPromptDraftVersion } from "@/lib/api/cases";
import { ApiError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/auth-provider";

const schema = z.object({
  content: z
    .string()
    .trim()
    .min(1, "Prompt content is required")
    .max(100_000, "Content is too long"),
});

export interface CreatePromptDraftDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  caseId: string;
  projectId: string;
}

export function CreatePromptDraftDialog({
  open,
  onOpenChange,
  caseId,
  projectId,
}: CreatePromptDraftDialogProps) {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const contentId = useId();

  const [content, setContent] = useState("");
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function reset() {
    setContent("");
    setFieldError(null);
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

    const parsed = schema.safeParse({ content });
    if (!parsed.success) {
      setFieldError(parsed.error.issues[0]?.message ?? "Invalid content");
      return;
    }

    if (!token) {
      setFormError("You must be signed in to create a prompt draft.");
      return;
    }

    setFieldError(null);
    setSubmitting(true);

    void (async () => {
      try {
        const version = await createPromptDraftVersion(token, caseId, {
          content: parsed.data.content,
        });
        await Promise.all([
          queryClient.invalidateQueries({ queryKey: caseQueryKey(caseId) }),
          queryClient.invalidateQueries({ queryKey: casesQueryKey(projectId) }),
        ]);
        toast.success("Prompt draft created", {
          description: `v${String(version.version_number)}`,
        });
        reset();
        onOpenChange(false);
      } catch (cause) {
        if (cause instanceof ApiError) {
          setFormError(cause.message);
        } else {
          setFormError("Could not create the prompt draft. Please try again.");
        }
      } finally {
        setSubmitting(false);
      }
    })();
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent
        className="sm:max-w-lg"
        showClose={!submitting}
        onPointerDownOutside={(event) => {
          if (submitting) event.preventDefault();
        }}
        onEscapeKeyDown={(event) => {
          if (submitting) event.preventDefault();
        }}
      >
        <DialogHeader>
          <DialogTitle>Create prompt draft</DialogTitle>
          <DialogDescription>
            Add a new draft of the agent instructions for this case. Publish it when ready, or pin
            the draft from a case version (publishing the case version also publishes a pinned
            draft).
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={onSubmit} className="space-y-4" noValidate>
          {formError ? <InlineError density="block">{formError}</InlineError> : null}

          <div className="space-y-1.5">
            <Label htmlFor={contentId}>Content</Label>
            <Textarea
              id={contentId}
              name="content"
              value={content}
              autoFocus
              disabled={submitting}
              rows={10}
              className="font-mono text-[length:var(--ef-text-caption)]"
              placeholder="Instructions for the agent…"
              onChange={(event) => {
                setContent(event.target.value);
                if (fieldError) setFieldError(null);
              }}
              aria-invalid={fieldError ? true : undefined}
            />
            {fieldError ? <InlineError>{fieldError}</InlineError> : null}
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
