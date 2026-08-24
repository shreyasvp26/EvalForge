"use client";

import { useQuery } from "@tanstack/react-query";

import { runEventsQueryKey } from "../utils";

import { useRunPolling } from "./use-run-polling";

import type { RunStatus } from "@/lib/api/runs";

import { listRunEvents } from "@/lib/api/runs";
import { useAuth } from "@/lib/auth/auth-provider";

export function useRunEvents(runId: string, status: RunStatus | undefined, enabled = true) {
  const { token } = useAuth();
  const polling = useRunPolling(status);

  return useQuery({
    queryKey: runEventsQueryKey(runId),
    enabled: Boolean(token) && Boolean(runId) && enabled,
    queryFn: async () => {
      if (!token) throw new Error("Missing auth token");
      return listRunEvents(token, runId, { limit: 100, sort: "sequence" });
    },
    refetchInterval: polling.refetchInterval,
  });
}
