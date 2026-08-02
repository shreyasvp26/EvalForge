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

import { casesQueryKey } from "./utils";

import { InlineError } from "@/components/patterns/inline-error";
import { createCase } from "@/lib/api/cases";
import { ApiError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/auth-provider";

const schema = z.object({
  name: z.string().trim().min(1, "Name is required").max(200, "Name is too long"),
  description: z.string().max(2000, "Description is too long"),
});

export interface CreateCaseDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectId: string;
  onCreated?: (caseId: string) => void;
}

export function CreateCaseDialog({
  open,
  onOpenChange,
  projectId,
  onCreated,
}: CreateCaseDialogProps) {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const nameId = useId();
  const descriptionId = useId();

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [fieldErrors, setFieldErrors] = useState<{ name?: string; description?: string }>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function reset() {
    setName("");
    setDescription("");
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

    const parsed = schema.safeParse({ name, description });
    if (!parsed.success) {
      const nextErrors: { name?: string; description?: string } = {};
      for (const issue of parsed.error.issues) {
        const key = issue.path[0];
        if (key === "name" || key === "description") {
          nextErrors[key] = issue.message;
        }
      }
      setFieldErrors(nextErrors);
      return;
    }

    if (!token) {
      setFormError("You must be signed in to create a case.");
      return;
    }

    setFieldErrors({});
    setSubmitting(true);
    const idempotencyKey =
      typeof crypto !== "undefined" && "randomUUID" in crypto
        ? crypto.randomUUID()
        : `create-case-${String(Date.now())}`;

    void (async () => {
      try {
        const caseItem = await createCase(
          token,
          {
            project_id: projectId,
            name: parsed.data.name,
            description: parsed.data.description,
          },
          idempotencyKey,
        );
        await queryClient.invalidateQueries({ queryKey: casesQueryKey(projectId) });
        toast.success("Case created", { description: caseItem.name });
        reset();
        onOpenChange(false);
        onCreated?.(caseItem.id);
      } catch (cause) {
        if (cause instanceof ApiError) {
          setFormError(cause.message);
        } else {
          setFormError("Could not create the case. Please try again.");
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
          <DialogTitle>Create case</DialogTitle>
          <DialogDescription>
            Cases define an engineering task and own prompt versions. Add a prompt draft and case
            version after creation.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={onSubmit} className="space-y-4" noValidate>
          {formError ? <InlineError density="block">{formError}</InlineError> : null}

          <div className="space-y-1.5">
            <Label htmlFor={nameId}>Name</Label>
            <Input
              id={nameId}
              name="name"
              value={name}
              autoFocus
              disabled={submitting}
              placeholder="e.g. Fix checkout race"
              onChange={(event) => {
                setName(event.target.value);
                if (fieldErrors.name) {
                  setFieldErrors((current) => {
                    const next = { ...current };
                    delete next.name;
                    return next;
                  });
                }
              }}
              aria-invalid={fieldErrors.name ? true : undefined}
            />
            {fieldErrors.name ? <InlineError>{fieldErrors.name}</InlineError> : null}
          </div>

          <div className="space-y-1.5">
            <Label htmlFor={descriptionId}>Description</Label>
            <Textarea
              id={descriptionId}
              name="description"
              value={description}
              disabled={submitting}
              rows={3}
              placeholder="Optional context for collaborators"
              onChange={(event) => {
                setDescription(event.target.value);
                if (fieldErrors.description) {
                  setFieldErrors((current) => {
                    const next = { ...current };
                    delete next.description;
                    return next;
                  });
                }
              }}
              aria-invalid={fieldErrors.description ? true : undefined}
            />
            {fieldErrors.description ? <InlineError>{fieldErrors.description}</InlineError> : null}
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
              Create case
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
