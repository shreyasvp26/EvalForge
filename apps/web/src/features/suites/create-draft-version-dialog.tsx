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
  Plus,
  Text,
  Trash2,
  toast,
} from "@agent-eval/ui";
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { z } from "zod";

import { suiteQueryKey, suitesQueryKey } from "./utils";

import { InlineError } from "@/components/patterns/inline-error";
import { ApiError } from "@/lib/api/client";
import { createSuiteDraftVersion } from "@/lib/api/suites";
import { useAuth } from "@/lib/auth/auth-provider";

interface CompositionRow {
  id: string;
  case_version_id: string;
  position: string;
}

const entrySchema = z.object({
  case_version_id: z.string().trim().min(1, "Case version id is required"),
  position: z.coerce.number().int().min(0, "Position must be ≥ 0"),
  case_project_id: z.string().min(1),
});

export interface CreateDraftVersionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  suiteId: string;
  projectId: string;
}

export function CreateDraftVersionDialog({
  open,
  onOpenChange,
  suiteId,
  projectId,
}: CreateDraftVersionDialogProps) {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const [rows, setRows] = useState<CompositionRow[]>([
    { id: crypto.randomUUID(), case_version_id: "", position: "0" },
  ]);
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function reset() {
    setRows([{ id: crypto.randomUUID(), case_version_id: "", position: "0" }]);
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

    const composition = [];
    const positions = new Set<number>();
    const caseIds = new Set<string>();

    for (const row of rows) {
      const parsed = entrySchema.safeParse({
        case_version_id: row.case_version_id,
        position: row.position,
        case_project_id: projectId,
      });
      if (!parsed.success) {
        setFormError(parsed.error.issues[0]?.message ?? "Invalid composition row");
        return;
      }
      if (positions.has(parsed.data.position)) {
        setFormError(`Duplicate position: ${String(parsed.data.position)}`);
        return;
      }
      if (caseIds.has(parsed.data.case_version_id)) {
        setFormError("Each case version can only appear once in a suite.");
        return;
      }
      positions.add(parsed.data.position);
      caseIds.add(parsed.data.case_version_id);
      composition.push(parsed.data);
    }

    if (composition.length === 0) {
      setFormError("Add at least one case version.");
      return;
    }

    if (!token) {
      setFormError("You must be signed in.");
      return;
    }

    setSubmitting(true);
    void (async () => {
      try {
        const version = await createSuiteDraftVersion(token, suiteId, { composition });
        await Promise.all([
          queryClient.invalidateQueries({ queryKey: suiteQueryKey(suiteId) }),
          queryClient.invalidateQueries({ queryKey: suitesQueryKey(projectId) }),
        ]);
        toast.success("Draft version created", {
          description: `v${String(version.version_number)}`,
        });
        reset();
        onOpenChange(false);
      } catch (cause) {
        if (cause instanceof ApiError) {
          setFormError(cause.message);
        } else {
          setFormError("Could not create the draft version.");
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
          <DialogTitle>Create draft version</DialogTitle>
          <DialogDescription>
            Pin ordered case versions for this draft. Case project is fixed to this suite’s project.
            Full case pickers arrive with the Cases milestone.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={onSubmit} className="space-y-4" noValidate>
          {formError ? <InlineError density="block">{formError}</InlineError> : null}

          <div className="space-y-3">
            {rows.map((row, index) => (
              <div
                key={row.id}
                className="grid gap-2 rounded-[var(--ef-radius-control)] border border-border p-3 sm:grid-cols-[1fr_5.5rem_auto]"
              >
                <div className="space-y-1.5">
                  <Label htmlFor={`${row.id}-case`}>Case version id</Label>
                  <Input
                    id={`${row.id}-case`}
                    value={row.case_version_id}
                    disabled={submitting}
                    placeholder="case version id"
                    onChange={(event) => {
                      const value = event.target.value;
                      setRows((current) =>
                        current.map((item, i) =>
                          i === index ? { ...item, case_version_id: value } : item,
                        ),
                      );
                    }}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor={`${row.id}-pos`}>Position</Label>
                  <Input
                    id={`${row.id}-pos`}
                    type="number"
                    min={0}
                    step={1}
                    value={row.position}
                    disabled={submitting}
                    onChange={(event) => {
                      const value = event.target.value;
                      setRows((current) =>
                        current.map((item, i) =>
                          i === index ? { ...item, position: value } : item,
                        ),
                      );
                    }}
                  />
                </div>
                <div className="flex items-end">
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    leftIcon={Trash2}
                    disabled={submitting || rows.length <= 1}
                    aria-label={`Remove row ${String(index + 1)}`}
                    onClick={() => {
                      setRows((current) => current.filter((_, i) => i !== index));
                    }}
                  >
                    Remove
                  </Button>
                </div>
              </div>
            ))}
          </div>

          <Text variant="caption">Project id for all entries: {projectId}</Text>

          <DialogFooter className="flex-col gap-2 sm:flex-row sm:justify-between">
            <Button
              type="button"
              variant="outline"
              leftIcon={Plus}
              disabled={submitting}
              onClick={() => {
                setRows((current) => [
                  ...current,
                  {
                    id: crypto.randomUUID(),
                    case_version_id: "",
                    position: String(current.length),
                  },
                ]);
              }}
            >
              Add case
            </Button>
            <div className="flex gap-2">
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
            </div>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
