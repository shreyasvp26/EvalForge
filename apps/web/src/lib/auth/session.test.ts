import { afterEach, describe, expect, it, vi } from "vitest";

import {
  clearAccessToken,
  hasSessionCookie,
  persistAccessToken,
  readAccessToken,
  syncSessionCookie,
} from "./session";

const TOKEN_KEY = "evalforge.auth.token";
const EXPIRES_AT_KEY = "evalforge.auth.expires_at";

describe("hasSessionCookie", () => {
  it("detects the session presence cookie", () => {
    expect(hasSessionCookie("evalforge.auth=1; theme=dark")).toBe(true);
    expect(hasSessionCookie("theme=dark")).toBe(false);
    expect(hasSessionCookie(null)).toBe(false);
  });
});

describe("session cookie / JWT synchronization", () => {
  const store = new Map<string, string>();
  let cookieJar = "";

  afterEach(() => {
    store.clear();
    cookieJar = "";
    vi.unstubAllGlobals();
  });

  function stubBrowser() {
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
  }

  it("persistAccessToken writes JWT and presence cookie together", () => {
    stubBrowser();
    persistAccessToken("jwt-token", 3600);
    expect(readAccessToken()).toBe("jwt-token");
    expect(hasSessionCookie(cookieJar)).toBe(true);
  });

  it("clearAccessToken removes JWT and cookie (logout path)", () => {
    stubBrowser();
    persistAccessToken("jwt-token", 3600);
    clearAccessToken();
    expect(readAccessToken()).toBeNull();
    expect(hasSessionCookie(cookieJar)).toBe(false);
  });

  it("syncSessionCookie restores cookie when JWT exists without cookie", () => {
    stubBrowser();
    store.set(TOKEN_KEY, "jwt-token");
    store.set(EXPIRES_AT_KEY, String(Date.now() + 60_000));
    expect(hasSessionCookie(cookieJar)).toBe(false);
    syncSessionCookie();
    expect(hasSessionCookie(cookieJar)).toBe(true);
  });

  it("syncSessionCookie clears cookie when JWT is missing", () => {
    stubBrowser();
    cookieJar = "evalforge.auth=1";
    syncSessionCookie();
    expect(hasSessionCookie(cookieJar)).toBe(false);
  });

  it("expired JWT is treated as absent and clears storage", () => {
    stubBrowser();
    store.set(TOKEN_KEY, "expired-jwt");
    store.set(EXPIRES_AT_KEY, String(Date.now() - 1_000));
    expect(readAccessToken()).toBeNull();
    expect(store.has(TOKEN_KEY)).toBe(false);
  });
});
