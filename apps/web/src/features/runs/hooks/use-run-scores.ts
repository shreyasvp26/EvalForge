"use client";

import { useQuery } from "@tanstack/react-query";

import { runScoresQueryKey } from "../utils";

import { useRunPolling } from "./use-run-polling";

import type { RunStatus } from "@/lib/api/runs";

import { listRunScores } from "@/lib/api/runs";
import { useAuth } from "@/lib/auth/auth-provider";

export function useRunScores(runId: string, status: RunStatus | undefined, enabled = true) {
  const { token } = useAuth();
  const polling = useRunPolling(status);

  return useQuery({
    queryKey: runScoresQueryKey(runId),
    enabled: Boolean(token) && Boolean(runId) && enabled,
    queryFn: async () => {
      if (!token) throw new Error("Missing auth token");
      return listRunScores(token, runId, { limit: 100 });
    },
    refetchInterval: polling.refetchInterval,
  });
}
