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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Textarea,
  toast,
} from "@agent-eval/ui";
import { useQueryClient } from "@tanstack/react-query";
import { useId, useState } from "react";
import { z } from "zod";

import { GRADER_FAMILIES, gradersQueryKey } from "./utils";

import { InlineError } from "@/components/patterns/inline-error";
import { ApiError } from "@/lib/api/client";
import { createGrader } from "@/lib/api/graders";
import { useAuth } from "@/lib/auth/auth-provider";

const schema = z.object({
  name: z.string().trim().min(1, "Name is required").max(200, "Name is too long"),
  family: z.enum(["objective", "rubric"], { message: "Select a grader family" }),
  description: z.string().max(2000, "Description is too long"),
});

export interface CreateGraderDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated?: (graderId: string) => void;
}

export function CreateGraderDialog({ open, onOpenChange, onCreated }: CreateGraderDialogProps) {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const nameId = useId();
  const descriptionId = useId();

  const [name, setName] = useState("");
  const [family, setFamily] = useState("");
  const [description, setDescription] = useState("");
  const [fieldErrors, setFieldErrors] = useState<{
    name?: string;
    family?: string;
    description?: string;
  }>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function reset() {
    setName("");
    setFamily("");
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

    const parsed = schema.safeParse({ name, family, description });
    if (!parsed.success) {
      const nextErrors: { name?: string; family?: string; description?: string } = {};
      for (const issue of parsed.error.issues) {
        const key = issue.path[0];
        if (key === "name" || key === "family" || key === "description") {
          nextErrors[key] = issue.message;
        }
      }
      setFieldErrors(nextErrors);
      return;
    }

    if (!token) {
      setFormError("You must be signed in to create a grader.");
      return;
    }

    setFieldErrors({});
    setSubmitting(true);
    const idempotencyKey =
      typeof crypto !== "undefined" && "randomUUID" in crypto
        ? crypto.randomUUID()
        : `create-grader-${String(Date.now())}`;

    void (async () => {
      try {
        const grader = await createGrader(
          token,
          {
            name: parsed.data.name,
            family: parsed.data.family,
            description: parsed.data.description,
          },
          idempotencyKey,
        );
        await queryClient.invalidateQueries({ queryKey: gradersQueryKey });
        toast.success("Grader created", { description: grader.name });
        reset();
        onOpenChange(false);
        onCreated?.(grader.id);
      } catch (cause) {
        if (cause instanceof ApiError) {
          setFormError(cause.message);
        } else {
          setFormError("Could not create the grader. Please try again.");
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
          <DialogTitle>Create grader</DialogTitle>
          <DialogDescription>
            Graders are platform catalog entries that score agent runs. Choose a family, then add
            draft versions with a specification after creation.
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
              placeholder="e.g. Diff presence"
              onChange={(event) => {
                setName(event.target.value);
                if (fieldErrors.name) {
                  setFieldErrors((current) => {
                    const { name: _removed, ...rest } = current;
                    return rest;
                  });
                }
              }}
              aria-invalid={fieldErrors.name ? true : undefined}
            />
            {fieldErrors.name ? <InlineError>{fieldErrors.name}</InlineError> : null}
          </div>

          <div className="space-y-1.5">
            <Label>Family</Label>
            <Select
              {...(family ? { value: family } : {})}
              onValueChange={(value) => {
                setFamily(value);
                if (fieldErrors.family) {
                  setFieldErrors((current) => {
                    const { family: _removed, ...rest } = current;
                    return rest;
                  });
                }
              }}
              disabled={submitting}
            >
              <SelectTrigger aria-invalid={fieldErrors.family ? true : undefined}>
                <SelectValue placeholder="Select family" />
              </SelectTrigger>
              <SelectContent>
                {GRADER_FAMILIES.map((item) => (
                  <SelectItem key={item.value} value={item.value}>
                    {item.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {fieldErrors.family ? <InlineError>{fieldErrors.family}</InlineError> : null}
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
                    const { description: _removed, ...rest } = current;
                    return rest;
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
              Create grader
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
