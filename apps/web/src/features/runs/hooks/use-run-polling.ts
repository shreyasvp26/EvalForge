"use client";

import { isLiveRunStatus } from "../utils";

import type { RunStatus } from "@/lib/api/runs";

/** Polling interval while a run is queued / running / grading. */
export const RUN_POLL_INTERVAL_MS = 2500;

/**
 * Live refresh strategy for a run.
 *
 * Today this returns a React Query `refetchInterval`.
 * When SSE lands, replace the body of this hook (open EventSource, invalidate
 * query keys on message) and keep returning `{ isLive, refetchInterval: false }`
 * so `useRun` / `useRunEvents` / `useRunArtifacts` / `useRunScores` stay unchanged.
 */
export function useRunPolling(status: RunStatus | undefined): {
  isLive: boolean;
  refetchInterval: number | false;
} {
  const isLive = isLiveRunStatus(status);
  return {
    isLive,
    refetchInterval: isLive ? RUN_POLL_INTERVAL_MS : false,
  };
}

/** Pure helper for useQuery refetchInterval callbacks that already have status. */
export function getRunRefetchInterval(status: RunStatus | undefined): number | false {
  return isLiveRunStatus(status) ? RUN_POLL_INTERVAL_MS : false;
}
