"use client";

import { Badge, Button, Cluster, Text, toast } from "@agent-eval/ui";
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import {
  formatGraderDate,
  graderQueryKey,
  gradersQueryKey,
  versionStatusBadge,
  versionStatusLabel,
} from "./utils";

import type { Grader, GraderVersion } from "@/lib/api/graders";

import { ApiError } from "@/lib/api/client";
import { publishGraderVersion } from "@/lib/api/graders";
import { useAuth } from "@/lib/auth/auth-provider";

export interface GraderVersionCardsProps {
  grader: Grader;
  versions: GraderVersion[];
}

export function GraderVersionCards({ grader, versions }: GraderVersionCardsProps) {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const [busyId, setBusyId] = useState<string | null>(null);

  async function refresh() {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: graderQueryKey(grader.id) }),
      queryClient.invalidateQueries({ queryKey: gradersQueryKey }),
    ]);
  }

  async function onPublish(version: GraderVersion) {
    if (!token) return;
    setBusyId(version.id);
    try {
      await publishGraderVersion(token, grader.id, version.id);
      await refresh();
      toast.success("Grader version published", {
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
        No grader versions yet. Create a draft to attach a specification for scoring.
      </Text>
    );
  }

  return (
    <ul className="space-y-4">
      {versions.map((version) => {
        const isActive = version.id === grader.active_version_id;
        const canPublish = version.status === "draft" && grader.status !== "deprecated";
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
                    Version {String(version.version_number)}
                  </Text>
                  <Badge status={versionStatusBadge(version.status)}>
                    {versionStatusLabel(version.status)}
                  </Badge>
                  {isActive ? <Badge status="success">Current active</Badge> : null}
                </Cluster>
                <Text as="div" variant="body">
                  {version.label}
                </Text>
                <Text variant="caption" className="tabular-nums">
                  Created {formatGraderDate(version.created_at)}
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

            <div className="mt-4 space-y-1.5">
              <Text as="div" variant="caption">
                Specification
              </Text>
              <pre className="max-h-64 overflow-auto rounded-[var(--ef-radius-control)] border border-border bg-muted/40 p-3 font-mono text-[length:var(--ef-text-caption)] leading-relaxed text-foreground whitespace-pre-wrap break-words">
                {version.specification}
              </pre>
            </div>
          </li>
        );
      })}
    </ul>
  );
}
