"use client";

import {
  Button,
  Checkbox,
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
  Text,
  Textarea,
  toast,
} from "@agent-eval/ui";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useId, useMemo, useState } from "react";
import { z } from "zod";

import { canSubmitTaskRevision, isExactCommitSha } from "./repository-revision";
import { RepositoryRevisionSelector } from "./repository-revision-selector";
import { caseQueryKey, casesQueryKey, pinnablePromptVersions, versionStatusLabel } from "./utils";

import type { Case } from "@/lib/api/cases";

import { InlineError } from "@/components/patterns/inline-error";
import { gradersQueryKey } from "@/features/graders/utils";
import { createCaseDraftVersion } from "@/lib/api/cases";
import { ApiError } from "@/lib/api/client";
import { listGraders } from "@/lib/api/graders";
import { useAuth } from "@/lib/auth/auth-provider";

const schema = z.object({
  description: z
    .string()
    .trim()
    .min(1, "Description is required")
    .max(5000, "Description is too long"),
  repository_url: z
    .string()
    .trim()
    .min(1, "Repository URL is required")
    .max(2000, "URL is too long"),
  commit_sha: z
    .string()
    .trim()
    .min(1, "Commit SHA is required")
    .max(128, "Commit SHA is too long")
    .refine((value) => isExactCommitSha(value), {
      message: "Commit must be an exact hex SHA (7–40 chars), not a branch name",
    }),
  subdirectory: z.string().max(500, "Subdirectory is too long"),
  prompt_version_id: z.string().min(1, "Select a prompt version"),
  expected_checks: z.string().max(5000),
});

function splitList(value: string): string[] {
  return value
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

export interface CreateCaseDraftDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  caseItem: Case;
}

export function CreateCaseDraftDialog({
  open,
  onOpenChange,
  caseItem,
}: CreateCaseDraftDialogProps) {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const descriptionId = useId();
  const subdirId = useId();
  const checksId = useId();

  const promptOptions = useMemo(() => pinnablePromptVersions(caseItem), [caseItem]);

  const gradersQuery = useQuery({
    queryKey: [...gradersQueryKey, "case-draft"],
    enabled: Boolean(token) && open,
    queryFn: async () => {
      if (!token) throw new Error("Missing auth token");
      return listGraders(token, { limit: 100, sort: "-created_at" });
    },
  });

  const availableGraders = useMemo(() => {
    return (gradersQuery.data?.items ?? []).filter((grader) => grader.status !== "deprecated");
  }, [gradersQuery.data]);

  const [description, setDescription] = useState("");
  const [repositoryUrl, setRepositoryUrl] = useState("");
  const [commitSha, setCommitSha] = useState("");
  const [subdirectory, setSubdirectory] = useState("");
  const [promptVersionId, setPromptVersionId] = useState("");
  const [expectedChecks, setExpectedChecks] = useState("");
  const [selectedGraderIds, setSelectedGraderIds] = useState<Record<string, boolean>>({});
  const [fieldErrors, setFieldErrors] = useState<
    Partial<Record<keyof z.infer<typeof schema>, string>>
  >({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function reset() {
    setDescription("");
    setRepositoryUrl("");
    setCommitSha("");
    setSubdirectory("");
    setPromptVersionId("");
    setExpectedChecks("");
    setSelectedGraderIds({});
    setFieldErrors({});
    setFormError(null);
    setSubmitting(false);
  }

  function handleOpenChange(next: boolean) {
    if (submitting) return;
    if (!next) reset();
    onOpenChange(next);
  }

  function clearField(key: keyof z.infer<typeof schema>) {
    if (fieldErrors[key]) {
      setFieldErrors((current) => {
        const { [key]: _removed, ...rest } = current;
        return rest;
      });
    }
  }

  const onRevisionChange = useCallback((value: { repositoryUrl: string; commitSha: string }) => {
    setRepositoryUrl(value.repositoryUrl);
    setCommitSha(value.commitSha);
    setFieldErrors((current) => {
      if (!current.repository_url && !current.commit_sha) return current;
      return Object.fromEntries(
        Object.entries(current).filter(([key]) => key !== "repository_url" && key !== "commit_sha"),
      );
    });
  }, []);

  function toggleGrader(graderId: string, checked: boolean) {
    setSelectedGraderIds((current) => {
      if (!checked) {
        const { [graderId]: _removed, ...rest } = current;
        return rest;
      }
      return { ...current, [graderId]: true };
    });
  }

  function onSubmit(event: React.SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);

    if (promptOptions.length === 0) {
      setFormError("Create a prompt draft before creating a case version.");
      return;
    }

    const parsed = schema.safeParse({
      description,
      repository_url: repositoryUrl,
      commit_sha: commitSha,
      subdirectory,
      prompt_version_id: promptVersionId,
      expected_checks: expectedChecks,
    });

    if (!parsed.success) {
      const nextErrors: Partial<Record<keyof z.infer<typeof schema>, string>> = {};
      for (const issue of parsed.error.issues) {
        const key = issue.path[0];
        if (typeof key === "string" && !(key in nextErrors)) {
          nextErrors[key as keyof z.infer<typeof schema>] = issue.message;
        }
      }
      setFieldErrors(nextErrors);
      return;
    }

    if (!token) {
      setFormError("You must be signed in to create a case draft.");
      return;
    }

    setFieldErrors({});
    setSubmitting(true);

    void (async () => {
      try {
        const version = await createCaseDraftVersion(token, caseItem.id, {
          description: parsed.data.description,
          repository_url: parsed.data.repository_url,
          commit_sha: parsed.data.commit_sha,
          subdirectory: parsed.data.subdirectory.trim() || null,
          prompt_version_id: parsed.data.prompt_version_id,
          expected_checks: splitList(parsed.data.expected_checks),
          applicable_grader_ids: Object.keys(selectedGraderIds),
        });
        await Promise.all([
          queryClient.invalidateQueries({ queryKey: caseQueryKey(caseItem.id) }),
          queryClient.invalidateQueries({ queryKey: casesQueryKey(caseItem.project_id) }),
        ]);
        toast.success("Task draft created", {
          description: `v${String(version.version_number)}`,
        });
        reset();
        onOpenChange(false);
      } catch (cause) {
        if (cause instanceof ApiError) {
          setFormError(cause.message);
        } else {
          setFormError("Could not create the case draft. Please try again.");
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
          <DialogTitle>Create task draft</DialogTitle>
          <DialogDescription>
            Select a GitHub repository and pin an exact commit SHA. Publish when the definition is
            ready for evaluation runs.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={onSubmit} className="space-y-4" noValidate>
          {formError ? <InlineError density="block">{formError}</InlineError> : null}

          {promptOptions.length === 0 ? (
            <Text variant="secondary">
              No pinnable prompt versions yet. Create a prompt draft first.
            </Text>
          ) : (
            <div className="space-y-1.5">
              <Label>Prompt version</Label>
              <Select
                {...(promptVersionId ? { value: promptVersionId } : {})}
                onValueChange={(value) => {
                  setPromptVersionId(value);
                  clearField("prompt_version_id");
                }}
                disabled={submitting}
              >
                <SelectTrigger aria-invalid={fieldErrors.prompt_version_id ? true : undefined}>
                  <SelectValue placeholder="Select a prompt version" />
                </SelectTrigger>
                <SelectContent>
                  {promptOptions.map((version) => (
                    <SelectItem key={version.id} value={version.id}>
                      {`v${String(version.version_number)} · ${versionStatusLabel(version.status)}`}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {fieldErrors.prompt_version_id ? (
                <InlineError>{fieldErrors.prompt_version_id}</InlineError>
              ) : null}
            </div>
          )}

          <div className="space-y-1.5">
            <Label htmlFor={descriptionId}>Task description</Label>
            <Textarea
              id={descriptionId}
              value={description}
              disabled={submitting}
              rows={3}
              placeholder="What should the agent accomplish?"
              onChange={(event) => {
                setDescription(event.target.value);
                clearField("description");
              }}
              aria-invalid={fieldErrors.description ? true : undefined}
            />
            {fieldErrors.description ? <InlineError>{fieldErrors.description}</InlineError> : null}
          </div>

          <RepositoryRevisionSelector
            disabled={submitting}
            repositoryUrl={repositoryUrl}
            commitSha={commitSha}
            onChange={onRevisionChange}
            repositoryError={fieldErrors.repository_url ?? null}
            commitError={fieldErrors.commit_sha ?? null}
          />

          <div className="space-y-1.5">
            <Label htmlFor={subdirId}>Subdirectory (optional)</Label>
            <Input
              id={subdirId}
              value={subdirectory}
              disabled={submitting}
              placeholder="packages/app"
              onChange={(event) => {
                setSubdirectory(event.target.value);
                clearField("subdirectory");
              }}
              aria-invalid={fieldErrors.subdirectory ? true : undefined}
            />
            {fieldErrors.subdirectory ? (
              <InlineError>{fieldErrors.subdirectory}</InlineError>
            ) : null}
          </div>

          <div className="space-y-1.5">
            <Label htmlFor={checksId}>Expected checks (optional)</Label>
            <Textarea
              id={checksId}
              value={expectedChecks}
              disabled={submitting}
              rows={2}
              placeholder="One per line or comma-separated, e.g. pytest"
              onChange={(event) => {
                setExpectedChecks(event.target.value);
                clearField("expected_checks");
              }}
            />
            <Text variant="caption">Comma or newline separated.</Text>
          </div>

          <div className="space-y-2">
            <Label>Applicable graders</Label>
            <Text variant="caption">
              Graders declared here can be pinned when launching a run against this case version.
            </Text>
            {gradersQuery.isLoading ? (
              <Text variant="secondary">Loading graders…</Text>
            ) : availableGraders.length === 0 ? (
              <Text variant="secondary">
                No graders available. Create a grader first, then declare it on this case.
              </Text>
            ) : (
              <ul className="max-h-48 divide-y divide-border overflow-y-auto rounded-[var(--ef-radius-panel)] border border-border">
                {availableGraders.map((grader) => (
                  <li key={grader.id} className="px-3 py-2">
                    <label className="flex items-center gap-3">
                      <Checkbox
                        checked={Boolean(selectedGraderIds[grader.id])}
                        disabled={submitting}
                        onCheckedChange={(value) => {
                          toggleGrader(grader.id, value === true);
                        }}
                      />
                      <span className="min-w-0 flex-1">
                        <span className="font-medium">{grader.name}</span>
                        <Text as="span" variant="caption" className="ml-2">
                          {grader.family}
                        </Text>
                      </span>
                    </label>
                  </li>
                ))}
              </ul>
            )}
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
            <Button
              type="submit"
              loading={submitting}
              disabled={
                promptOptions.length === 0 || !canSubmitTaskRevision({ repositoryUrl, commitSha })
              }
            >
              Create draft
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
