"use client";

import { useQuery } from "@tanstack/react-query";

import { runQueryKey } from "../utils";

import { getRunRefetchInterval } from "./use-run-polling";

import { getRun } from "@/lib/api/runs";
import { useAuth } from "@/lib/auth/auth-provider";

export function useRun(runId: string) {
  const { token } = useAuth();

  return useQuery({
    queryKey: runQueryKey(runId),
    enabled: Boolean(token) && Boolean(runId),
    queryFn: async () => {
      if (!token) throw new Error("Missing auth token");
      return getRun(token, runId);
    },
    refetchInterval: (query) => getRunRefetchInterval(query.state.data?.status),
  });
}
