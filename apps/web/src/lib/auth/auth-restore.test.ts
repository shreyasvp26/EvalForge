import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AUTH_RESTORE_TIMEOUT_MS } from "./constants";
import { resolveSessionRestore } from "./resolve-session-restore";
import {
  clearAccessToken,
  hasSessionCookie,
  persistAccessToken,
  readAccessToken,
  syncSessionCookie,
} from "./session";

describe("session restore decisions", () => {
  it("exposes a bounded restore timeout", () => {
    expect(AUTH_RESTORE_TIMEOUT_MS).toBeLessThanOrEqual(5_000);
    expect(AUTH_RESTORE_TIMEOUT_MS).toBeGreaterThan(0);
  });

  it("treats missing token as unauthenticated immediately", async () => {
    const outcome = await resolveSessionRestore({
      token: null,
      fetchMe: () => Promise.reject(new Error("should not be called")),
    });
    expect(outcome).toEqual({ status: "unauthenticated", reason: "missing_token" });
  });

  it("authenticates when /me succeeds", async () => {
    const outcome = await resolveSessionRestore({
      token: "ok",
      fetchMe: () => Promise.resolve({ id: "u1" }),
    });
    expect(outcome.status).toBe("authenticated");
  });

  it("clears to unauthenticated on 401", async () => {
    const outcome = await resolveSessionRestore({
      token: "bad",
      fetchMe: () => Promise.reject(Object.assign(new Error("Unauthorized"), { status: 401 })),
    });
    expect(outcome).toEqual({ status: "unauthenticated", reason: "unauthorized" });
  });

  it("fails restore on timeout instead of hanging", async () => {
    const outcome = await resolveSessionRestore({
      token: "slow",
      timeoutMs: 50,
      fetchMe: (_token, signal) =>
        new Promise((_resolve, reject) => {
          signal.addEventListener("abort", () => {
            reject(new DOMException("Aborted", "AbortError"));
          });
        }),
    });
    expect(outcome.status).toBe("restore_failed");
    if (outcome.status === "restore_failed") {
      expect(outcome.reason).toBe("timeout");
    }
  });

  it("fails restore on network errors without trapping forever", async () => {
    const outcome = await resolveSessionRestore({
      token: "net",
      fetchMe: () =>
        Promise.reject(
          Object.assign(new Error("Unable to reach the EvalForge API"), { status: 0 }),
        ),
    });
    expect(outcome.status).toBe("restore_failed");
    if (outcome.status === "restore_failed") {
      expect(outcome.reason).toBe("network");
    }
  });
});

describe("session cookie / JWT synchronization", () => {
  const store = new Map<string, string>();
  let cookieJar = "";

  const TOKEN_KEY = "evalforge.auth.token";
  const EXPIRES_AT_KEY = "evalforge.auth.expires_at";

  beforeEach(() => {
    store.clear();
    cookieJar = "";
    vi.stubGlobal("window", {
      localStorage: {
        getItem: (key: string) => store.get(key) ?? null,
        setItem: (key: string, value: string) => {
          store.set(key, value);
        },
        removeItem: (key: string) => {
          store.delete(key);
        },
      },
    });
    vi.stubGlobal("document", {
      get cookie() {
        return cookieJar;
      },
      set cookie(value: string) {
        const [pair] = value.split(";");
        if (!pair) return;
        const [name, raw] = pair.split("=");
        if (!name) return;
        const remaining = cookieJar
          .split("; ")
          .filter((part) => part && !part.startsWith(`${name}=`));
        if (value.includes("Max-Age=0")) {
          cookieJar = remaining.join("; ");
          return;
        }
        remaining.push(`${name}=${raw ?? ""}`);
        cookieJar = remaining.join("; ");
      },
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("persistAccessToken writes JWT and presence cookie together", () => {
    persistAccessToken("jwt-token", 3600);
    expect(readAccessToken()).toBe("jwt-token");
    expect(hasSessionCookie(cookieJar)).toBe(true);
  });

  it("clearAccessToken removes JWT and cookie", () => {
    persistAccessToken("jwt-token", 3600);
    clearAccessToken();
    expect(readAccessToken()).toBeNull();
    expect(hasSessionCookie(cookieJar)).toBe(false);
  });

  it("syncSessionCookie restores cookie when JWT exists without cookie", () => {
    store.set(TOKEN_KEY, "jwt-token");
    store.set(EXPIRES_AT_KEY, String(Date.now() + 60_000));
    expect(hasSessionCookie(cookieJar)).toBe(false);
    syncSessionCookie();
    expect(hasSessionCookie(cookieJar)).toBe(true);
  });
});
