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

import { graderQueryKey, gradersQueryKey } from "./utils";

import { InlineError } from "@/components/patterns/inline-error";
import { ApiError } from "@/lib/api/client";
import { createGraderDraftVersion } from "@/lib/api/graders";
import { useAuth } from "@/lib/auth/auth-provider";

const schema = z.object({
  label: z.string().trim().min(1, "Label is required").max(200, "Label is too long"),
  specification: z
    .string()
    .trim()
    .min(1, "Specification is required")
    .max(200_000, "Specification is too long"),
});

export interface CreateGraderDraftDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  graderId: string;
}

export function CreateGraderDraftDialog({
  open,
  onOpenChange,
  graderId,
}: CreateGraderDraftDialogProps) {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const labelId = useId();
  const specId = useId();

  const [label, setLabel] = useState("");
  const [specification, setSpecification] = useState("");
  const [fieldErrors, setFieldErrors] = useState<{ label?: string; specification?: string }>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function reset() {
    setLabel("");
    setSpecification("");
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

    const parsed = schema.safeParse({ label, specification });
    if (!parsed.success) {
      const nextErrors: { label?: string; specification?: string } = {};
      for (const issue of parsed.error.issues) {
        const key = issue.path[0];
        if (key === "label" || key === "specification") {
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
        const version = await createGraderDraftVersion(token, graderId, {
          label: parsed.data.label,
          specification: parsed.data.specification,
        });
        await Promise.all([
          queryClient.invalidateQueries({ queryKey: graderQueryKey(graderId) }),
          queryClient.invalidateQueries({ queryKey: gradersQueryKey }),
        ]);
        toast.success("Grader draft created", {
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
        className="max-h-[90vh] overflow-y-auto sm:max-w-lg"
        showClose={!submitting}
        onPointerDownOutside={(event) => {
          if (submitting) event.preventDefault();
        }}
        onEscapeKeyDown={(event) => {
          if (submitting) event.preventDefault();
        }}
      >
        <DialogHeader>
          <DialogTitle>Create grader draft</DialogTitle>
          <DialogDescription>
            Add a draft specification for this grader. Publish when it is ready to score runs.
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
              placeholder="e.g. pytest-v1"
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
            <Label htmlFor={specId}>Specification</Label>
            <Textarea
              id={specId}
              value={specification}
              disabled={submitting}
              rows={12}
              className="font-mono text-[length:var(--ef-text-caption)]"
              placeholder="Opaque grader specification (instructions, check id, rubric text…)"
              onChange={(event) => {
                setSpecification(event.target.value);
                if (fieldErrors.specification) {
                  setFieldErrors((current) => {
                    const { specification: _removed, ...rest } = current;
                    return rest;
                  });
                }
              }}
              aria-invalid={fieldErrors.specification ? true : undefined}
            />
            {fieldErrors.specification ? (
              <InlineError>{fieldErrors.specification}</InlineError>
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
