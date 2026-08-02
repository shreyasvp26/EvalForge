"use client";

import { Badge, Button, Cluster, Text, toast } from "@agent-eval/ui";
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import {
  formatCaseDate,
  caseQueryKey,
  casesQueryKey,
  versionStatusBadge,
  versionStatusLabel,
} from "./utils";

import type { Case, PromptVersion } from "@/lib/api/cases";

import { publishPromptVersion } from "@/lib/api/cases";
import { ApiError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/auth-provider";

export interface PromptVersionCardsProps {
  caseItem: Case;
  versions: PromptVersion[];
}

export function PromptVersionCards({ caseItem, versions }: PromptVersionCardsProps) {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const [busyId, setBusyId] = useState<string | null>(null);

  async function refresh() {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: caseQueryKey(caseItem.id) }),
      queryClient.invalidateQueries({ queryKey: casesQueryKey(caseItem.project_id) }),
    ]);
  }

  async function onPublish(version: PromptVersion) {
    if (!token) return;
    setBusyId(version.id);
    try {
      await publishPromptVersion(token, caseItem.id, version.id);
      await refresh();
      toast.success("Prompt version published", {
        description: `v${String(version.version_number)} is now active`,
      });
    } catch (cause) {
      toast.error("Publish failed", {
        description: cause instanceof ApiError ? cause.message : "Please try again.",
      });
    } finally {
      setBusyId(null);
    }
  }

  if (versions.length === 0) {
    return (
      <Text variant="secondary">
        No prompt versions yet. Create a prompt draft to define agent instructions for this case.
      </Text>
    );
  }

  return (
    <ul className="space-y-4">
      {versions.map((version) => {
        const isActive = version.id === caseItem.active_prompt_version_id;
        const canPublish = version.status === "draft" && caseItem.status !== "deprecated";
        const isBusy = busyId === version.id;

        return (
          <li
            key={version.id}
            className="rounded-[var(--ef-radius-panel)] border border-border bg-card p-4 shadow-ef-sm"
          >
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div className="min-w-0 space-y-1">
                <Cluster gap={2} className="items-center">
                  <Text as="span" variant="body" className="font-medium">
                    Prompt v{String(version.version_number)}
                  </Text>
                  <Badge status={versionStatusBadge(version.status)}>
                    {versionStatusLabel(version.status)}
                  </Badge>
                  {isActive ? <Badge status="success">Current active</Badge> : null}
                </Cluster>
                <Text variant="caption" className="tabular-nums">
                  Created {formatCaseDate(version.created_at)}
                </Text>
                <Text variant="caption" className="break-all font-mono text-muted-foreground">
                  {version.id}
                </Text>
              </div>
              {canPublish ? (
                <Button
                  type="button"
                  size="sm"
                  loading={isBusy}
                  onClick={() => {
                    void onPublish(version);
                  }}
                >
                  Publish
                </Button>
              ) : null}
            </div>

            <pre className="mt-4 max-h-48 overflow-auto rounded-[var(--ef-radius-control)] border border-border bg-muted/40 p-3 font-mono text-[length:var(--ef-text-caption)] leading-relaxed text-foreground whitespace-pre-wrap break-words">
              {version.content}
            </pre>
          </li>
        );
      })}
    </ul>
  );
}
