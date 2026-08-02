"use client";

import { Badge, Button, Cluster, Text, toast } from "@agent-eval/ui";
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { SuiteCompositionViewer } from "./suite-composition-viewer";
import {
  formatSuiteDate,
  suiteQueryKey,
  suitesQueryKey,
  versionStatusBadge,
  versionStatusLabel,
} from "./utils";

import type { Suite, SuiteVersion } from "@/lib/api/suites";

import { ConfirmationDialog } from "@/components/patterns/confirmation-dialog";
import { ApiError } from "@/lib/api/client";
import { publishSuiteVersion, retireSuiteVersion } from "@/lib/api/suites";
import { useAuth } from "@/lib/auth/auth-provider";

export interface SuiteVersionCardsProps {
  suite: Suite;
  versions: SuiteVersion[];
}

export function SuiteVersionCards({ suite, versions }: SuiteVersionCardsProps) {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const [busyId, setBusyId] = useState<string | null>(null);
  const [retireTarget, setRetireTarget] = useState<SuiteVersion | null>(null);

  async function refresh() {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: suiteQueryKey(suite.id) }),
      queryClient.invalidateQueries({ queryKey: suitesQueryKey(suite.project_id) }),
    ]);
  }

  async function onPublish(version: SuiteVersion) {
    if (!token) return;
    setBusyId(version.id);
    try {
      await publishSuiteVersion(token, suite.id, version.id);
      await refresh();
      toast.success("Version published", {
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
        No versions yet. Create a draft to pin case versions and define execution order.
      </Text>
    );
  }

  return (
    <>
      <ul className="space-y-4">
        {versions.map((version) => {
          const isActive = version.id === suite.active_version_id;
          const canPublish = version.status === "draft";
          const canRetire = version.status === "active";
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
                  <Text variant="caption" className="tabular-nums">
                    Created {formatSuiteDate(version.created_at)}
                    {version.predecessor_version_id
                      ? ` · predecessor ${version.predecessor_version_id}`
                      : ""}
                  </Text>
                  <Text variant="caption" className="break-all font-mono text-muted-foreground">
                    {version.id}
                  </Text>
                </div>
                <Cluster gap={2}>
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
                  {canRetire ? (
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      disabled={isBusy}
                      onClick={() => {
                        setRetireTarget(version);
                      }}
                    >
                      Retire
                    </Button>
                  ) : null}
                </Cluster>
              </div>

              <div className="mt-4">
                <Text as="div" variant="caption" className="mb-2">
                  Composition ({String(version.composition.length)})
                </Text>
                <SuiteCompositionViewer composition={version.composition} />
              </div>
            </li>
          );
        })}
      </ul>

      <ConfirmationDialog
        open={retireTarget !== null}
        onOpenChange={(open) => {
          if (!open) setRetireTarget(null);
        }}
        variant="destructive"
        title="Retire active version?"
        description={
          retireTarget ? (
            <>
              Version {String(retireTarget.version_number)} will move from active to retired.
              Publish another draft to establish a new active version.
            </>
          ) : null
        }
        confirmLabel="Retire version"
        onConfirm={async () => {
          if (!token || !retireTarget) throw new Error("Missing context");
          try {
            await retireSuiteVersion(token, suite.id, retireTarget.id);
            await refresh();
            toast.success("Version retired", {
              description: `v${String(retireTarget.version_number)}`,
            });
            setRetireTarget(null);
          } catch (cause) {
            toast.error("Retire failed", {
              description: cause instanceof ApiError ? cause.message : "Please try again.",
            });
            throw cause;
          }
        }}
      />
    </>
  );
}
