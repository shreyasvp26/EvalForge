import { AUTH_RESTORE_TIMEOUT_MS } from "./constants";

import { ApiError } from "@/lib/api/client";

/**
 * Pure restore decision — shared by AuthProvider and regression tests.
 */
export type RestoreOutcome =
  | { status: "unauthenticated"; reason: "missing_token" | "unauthorized" }
  | { status: "authenticated"; profile: unknown }
  | { status: "restore_failed"; reason: "timeout" | "network"; message: string };

export async function resolveSessionRestore(input: {
  token: string | null;
  fetchMe: (token: string, signal: AbortSignal) => Promise<unknown>;
  timeoutMs?: number;
}): Promise<RestoreOutcome> {
  if (!input.token) {
    return { status: "unauthenticated", reason: "missing_token" };
  }
  const timeoutMs = input.timeoutMs ?? AUTH_RESTORE_TIMEOUT_MS;
  const controller = new AbortController();
  const timer = setTimeout(() => {
    controller.abort();
  }, timeoutMs);
  try {
    const profile = await input.fetchMe(input.token, controller.signal);
    return { status: "authenticated", profile };
  } catch (cause) {
    const aborted =
      (cause instanceof DOMException && cause.name === "AbortError") ||
      (cause instanceof Error && cause.name === "AbortError");
    if (aborted) {
      return {
        status: "restore_failed",
        reason: "timeout",
        message: "Your session could not be restored in time.",
      };
    }
    if (cause instanceof ApiError && (cause.status === 401 || cause.status === 403)) {
      return { status: "unauthenticated", reason: "unauthorized" };
    }
    if (
      cause &&
      typeof cause === "object" &&
      "status" in cause &&
      (cause.status === 401 || cause.status === 403)
    ) {
      return { status: "unauthenticated", reason: "unauthorized" };
    }
    const message =
      cause instanceof ApiError
        ? cause.message
        : cause instanceof Error
          ? cause.message
          : "We couldn’t reach EvalForge to verify your session.";
    return { status: "restore_failed", reason: "network", message };
  } finally {
    clearTimeout(timer);
  }
}
