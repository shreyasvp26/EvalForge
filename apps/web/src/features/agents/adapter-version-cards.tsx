"use client";

import { Badge, Button, Cluster, Text, toast } from "@agent-eval/ui";
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import {
  adapterQueryKey,
  agentQueryKey,
  formatAgentDate,
  versionStatusBadge,
  versionStatusLabel,
} from "./utils";

import type { Adapter, AdapterVersion } from "@/lib/api/agents";

import { publishAdapterVersion } from "@/lib/api/agents";
import { ApiError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/auth-provider";

export interface AdapterVersionCardsProps {
  adapter: Adapter;
  versions: AdapterVersion[];
}

export function AdapterVersionCards({ adapter, versions }: AdapterVersionCardsProps) {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const [busyId, setBusyId] = useState<string | null>(null);

  async function refresh() {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: adapterQueryKey(adapter.id) }),
      queryClient.invalidateQueries({ queryKey: agentQueryKey(adapter.agent_id) }),
    ]);
  }

  async function onPublish(version: AdapterVersion) {
    if (!token) return;
    setBusyId(version.id);
    try {
      await publishAdapterVersion(token, adapter.id, version.id);
      await refresh();
      toast.success("Adapter version published", {
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
        No adapter versions yet. Create a draft to label a mapping release.
      </Text>
    );
  }

  return (
    <ul className="space-y-4">
      {versions.map((version) => {
        const isActive = version.id === adapter.active_version_id;
        const canPublish = version.status === "draft" && adapter.status !== "deprecated";
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
                  Created {formatAgentDate(version.created_at)}
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
            {version.notes.trim() ? (
              <Text as="div" variant="secondary" className="mt-3 whitespace-pre-wrap">
                {version.notes}
              </Text>
            ) : null}
          </li>
        );
      })}
    </ul>
  );
}
