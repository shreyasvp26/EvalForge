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

import type { Case, CaseVersion } from "@/lib/api/cases";

import { publishCaseVersion } from "@/lib/api/cases";
import { ApiError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/auth-provider";

export interface CaseVersionCardsProps {
  caseItem: Case;
  versions: CaseVersion[];
}

export function CaseVersionCards({ caseItem, versions }: CaseVersionCardsProps) {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const [busyId, setBusyId] = useState<string | null>(null);

  async function refresh() {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: caseQueryKey(caseItem.id) }),
      queryClient.invalidateQueries({ queryKey: casesQueryKey(caseItem.project_id) }),
    ]);
  }

  async function onPublish(version: CaseVersion) {
    if (!token) return;
    setBusyId(version.id);
    try {
      await publishCaseVersion(token, caseItem.id, version.id);
      await refresh();
      toast.success("Case version published", {
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
        No case versions yet. Create a draft to pin a repository checkout and prompt version.
      </Text>
    );
  }

  return (
    <ul className="space-y-4">
      {versions.map((version) => {
        const isActive = version.id === caseItem.active_version_id;
        const canPublish = version.status === "draft" && caseItem.status !== "deprecated";
        const isBusy = busyId === version.id;
        const prompt = caseItem.prompt_versions.find(
          (item) => item.id === version.prompt_version_id,
        );

        return (
          <li
            key={version.id}
            className="rounded-[var(--ef-radius-panel)] border border-border bg-card p-4 shadow-ef-sm"
          >
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div className="min-w-0 space-y-1">
                <Cluster gap={2} className="items-center">
                  <Text as="span" variant="body" className="font-medium">
                    Case v{String(version.version_number)}
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

            <dl className="mt-4 grid gap-3 sm:grid-cols-2">
              <div className="space-y-1 sm:col-span-2">
                <Text as="div" variant="caption">
                  Description
                </Text>
                <Text as="div" variant="secondary">
                  {version.description}
                </Text>
              </div>
              <div className="space-y-1 sm:col-span-2">
                <Text as="div" variant="caption">
                  Repository
                </Text>
                <Text
                  as="div"
                  variant="body"
                  className="break-all font-mono text-[length:var(--ef-text-caption)]"
                >
                  {version.repository_url}
                </Text>
              </div>
              <div className="space-y-1">
                <Text as="div" variant="caption">
                  Commit
                </Text>
                <Text
                  as="div"
                  variant="body"
                  className="font-mono text-[length:var(--ef-text-caption)]"
                >
                  {version.commit_sha}
                </Text>
              </div>
              <div className="space-y-1">
                <Text as="div" variant="caption">
                  Subdirectory
                </Text>
                <Text as="div" variant="secondary">
                  {version.subdirectory?.trim() ? version.subdirectory : "—"}
                </Text>
              </div>
              <div className="space-y-1 sm:col-span-2">
                <Text as="div" variant="caption">
                  Pinned prompt
                </Text>
                <Text
                  as="div"
                  variant="body"
                  className="break-all font-mono text-[length:var(--ef-text-caption)]"
                >
                  {prompt
                    ? `v${String(prompt.version_number)} · ${versionStatusLabel(prompt.status)} · ${version.prompt_version_id}`
                    : version.prompt_version_id}
                </Text>
              </div>
              <div className="space-y-1">
                <Text as="div" variant="caption">
                  Expected checks
                </Text>
                <Text as="div" variant="secondary">
                  {version.expected_checks.length > 0 ? version.expected_checks.join(", ") : "—"}
                </Text>
              </div>
              <div className="space-y-1">
                <Text as="div" variant="caption">
                  Grader IDs
                </Text>
                <Text
                  as="div"
                  variant="secondary"
                  className="break-all font-mono text-[length:var(--ef-text-caption)]"
                >
                  {version.applicable_grader_ids.length > 0
                    ? version.applicable_grader_ids.join(", ")
                    : "—"}
                </Text>
              </div>
            </dl>
          </li>
        );
      })}
    </ul>
  );
}
