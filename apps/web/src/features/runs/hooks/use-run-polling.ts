"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import {
  runArtifactsQueryKey,
  runEventsQueryKey,
  runQueryKey,
  runScoresQueryKey,
  isLiveRunStatus,
} from "../utils";

import type { RunStatus } from "@/lib/api/runs";

import { getApiBaseUrl } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/auth-provider";

/** Polling interval while a run is live and SSE is unavailable / disconnected. */
export const RUN_POLL_INTERVAL_MS = 2500;

export type RunLiveConnectionState = "idle" | "connecting" | "live" | "polling" | "closed";

interface SharedStream {
  source: EventSource;
  refs: number;
  lastEventId: string | null;
  listeners: Set<(state: RunLiveConnectionState) => void>;
  state: RunLiveConnectionState;
  reconnectTimer: number | null;
}

const streams = new Map<string, SharedStream>();

function notify(stream: SharedStream, state: RunLiveConnectionState) {
  stream.state = state;
  for (const listener of stream.listeners) {
    listener(state);
  }
}

function invalidateRun(queryClient: ReturnType<typeof useQueryClient>, runId: string) {
  void queryClient.invalidateQueries({ queryKey: runQueryKey(runId) });
  void queryClient.invalidateQueries({ queryKey: runEventsQueryKey(runId) });
  void queryClient.invalidateQueries({ queryKey: runArtifactsQueryKey(runId) });
  void queryClient.invalidateQueries({ queryKey: runScoresQueryKey(runId) });
}

/**
 * Live refresh strategy for a run.
 *
 * Prefers authenticated SSE (`/events/stream`) with a single shared EventSource
 * per run id. Falls back to React Query polling when SSE is down. Durable REST
 * lists remain the source of truth — SSE only invalidates query caches.
 */
export function useRunPolling(
  runId: string | undefined,
  status: RunStatus | undefined,
): {
  isLive: boolean;
  refetchInterval: number | false;
  connection: RunLiveConnectionState;
} {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const isLive = isLiveRunStatus(status);
  const [connection, setConnection] = useState<RunLiveConnectionState>("idle");

  useEffect(() => {
    if (!isLive || !token || !runId) {
      setConnection(isLive ? "polling" : status ? "closed" : "idle");
      return;
    }

    let stream = streams.get(runId);
    if (!stream) {
      const base = getApiBaseUrl().replace(/\/$/, "");
      const params = new URLSearchParams({ access_token: token });
      const url = `${base}/v1/runs/${encodeURIComponent(runId)}/events/stream?${params.toString()}`;
      const source = new EventSource(url);
      const created: SharedStream = {
        source,
        refs: 0,
        lastEventId: null,
        listeners: new Set(),
        state: "connecting",
        reconnectTimer: null,
      };
      streams.set(runId, created);
      stream = created;

      const onActivity = () => {
        notify(created, "live");
        invalidateRun(queryClient, runId);
      };

      source.addEventListener("execution_event", (event) => {
        if (event.lastEventId) {
          created.lastEventId = event.lastEventId;
        }
        onActivity();
      });
      source.addEventListener("run_status", onActivity);
      source.addEventListener("heartbeat", () => {
        notify(created, "live");
      });
      source.addEventListener("run_terminal", () => {
        notify(created, "closed");
        invalidateRun(queryClient, runId);
        source.close();
        streams.delete(runId);
      });
      source.onerror = () => {
        source.close();
        notify(created, "polling");
        if (streams.get(runId) === created) {
          streams.delete(runId);
        }
      };
    }

    stream.refs += 1;
    stream.listeners.add(setConnection);
    setConnection(stream.state);

    return () => {
      const current = streams.get(runId);
      if (!current) return;
      current.listeners.delete(setConnection);
      current.refs -= 1;
      if (current.refs <= 0) {
        current.source.close();
        if (current.reconnectTimer !== null) {
          window.clearTimeout(current.reconnectTimer);
        }
        streams.delete(runId);
      }
    };
  }, [isLive, token, runId, queryClient, status]);

  const sseLive = connection === "live";
  return {
    isLive,
    refetchInterval: isLive && !sseLive ? RUN_POLL_INTERVAL_MS : false,
    connection: !isLive
      ? status
        ? "closed"
        : "idle"
      : connection === "closed"
        ? "polling"
        : connection,
  };
}

/** Pure helper for useQuery refetchInterval callbacks that already have status. */
export function getRunRefetchInterval(status: RunStatus | undefined): number | false {
  return isLiveRunStatus(status) ? RUN_POLL_INTERVAL_MS : false;
}
