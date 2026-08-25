"use client";

import { useQuery } from "@tanstack/react-query";

import { runArtifactsQueryKey } from "../utils";

import { useRunPolling } from "./use-run-polling";

import type { RunStatus } from "@/lib/api/runs";

import { listRunArtifacts } from "@/lib/api/runs";
import { useAuth } from "@/lib/auth/auth-provider";

export function useRunArtifacts(runId: string, status: RunStatus | undefined, enabled = true) {
  const { token } = useAuth();
  const polling = useRunPolling(runId, status);

  return useQuery({
    queryKey: runArtifactsQueryKey(runId),
    enabled: Boolean(token) && Boolean(runId) && enabled,
    queryFn: async () => {
      if (!token) throw new Error("Missing auth token");
      return listRunArtifacts(token, runId, { limit: 100, sort: "-created_at" });
    },
    refetchInterval: polling.refetchInterval,
  });
}
