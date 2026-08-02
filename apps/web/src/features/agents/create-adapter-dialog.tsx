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
  toast,
} from "@agent-eval/ui";
import { useQueryClient } from "@tanstack/react-query";
import { useId, useState } from "react";
import { z } from "zod";

import { adapterQueryKey, agentQueryKey, agentsQueryKey } from "./utils";

import { InlineError } from "@/components/patterns/inline-error";
import { createAdapter } from "@/lib/api/agents";
import { ApiError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/auth-provider";

const schema = z.object({
  name: z.string().trim().min(1, "Name is required").max(200, "Name is too long"),
});

export interface CreateAdapterDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  agentId: string;
  onCreated?: (adapterId: string) => void;
}

export function CreateAdapterDialog({
  open,
  onOpenChange,
  agentId,
  onCreated,
}: CreateAdapterDialogProps) {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const nameId = useId();

  const [name, setName] = useState("");
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function reset() {
    setName("");
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

    const parsed = schema.safeParse({ name });
    if (!parsed.success) {
      setFieldError(parsed.error.issues[0]?.message ?? "Invalid name");
      return;
    }

    if (!token) {
      setFormError("You must be signed in to create an adapter.");
      return;
    }

    setFieldError(null);
    setSubmitting(true);
    const idempotencyKey =
      typeof crypto !== "undefined" && "randomUUID" in crypto
        ? crypto.randomUUID()
        : `create-adapter-${String(Date.now())}`;

    void (async () => {
      try {
        const adapter = await createAdapter(
          token,
          { agent_id: agentId, name: parsed.data.name },
          idempotencyKey,
        );
        await Promise.all([
          queryClient.invalidateQueries({ queryKey: agentQueryKey(agentId) }),
          queryClient.invalidateQueries({ queryKey: agentsQueryKey }),
          queryClient.invalidateQueries({ queryKey: adapterQueryKey(adapter.id) }),
        ]);
        toast.success("Adapter connected", { description: adapter.name });
        reset();
        onOpenChange(false);
        onCreated?.(adapter.id);
      } catch (cause) {
        if (cause instanceof ApiError) {
          setFormError(cause.message);
        } else {
          setFormError("Could not create the adapter. Please try again.");
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
          <DialogTitle>Connect adapter</DialogTitle>
          <DialogDescription>
            Each agent connects to exactly one adapter. The adapter translates vendor streams into
            platform events and is versioned independently.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={onSubmit} className="space-y-4" noValidate>
          {formError ? <InlineError density="block">{formError}</InlineError> : null}

          <div className="space-y-1.5">
            <Label htmlFor={nameId}>Name</Label>
            <Input
              id={nameId}
              value={name}
              autoFocus
              disabled={submitting}
              placeholder="e.g. Claude Code adapter"
              onChange={(event) => {
                setName(event.target.value);
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
              Connect adapter
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
