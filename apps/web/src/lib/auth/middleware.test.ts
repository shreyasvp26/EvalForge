import { describe, expect, it } from "vitest";

import { middleware } from "../../middleware";

function request(path: string, cookie?: string) {
  const headers = new Headers();
  if (cookie) headers.set("cookie", cookie);
  return {
    nextUrl: {
      pathname: path,
      search: "",
      searchParams: new URLSearchParams(),
    },
    url: `http://localhost:3000${path}`,
    headers: {
      get: (name: string) => headers.get(name),
    },
  } as Parameters<typeof middleware>[0];
}

describe("auth middleware", () => {
  it("allows /login without a session cookie (no redirect loop)", () => {
    const response = middleware(request("/login"));
    expect(response.headers.get("location")).toBeNull();
  });

  it("allows /login even when a stale presence cookie exists", () => {
    const response = middleware(request("/login", "evalforge.auth=1"));
    expect(response.headers.get("location")).toBeNull();
  });

  it("redirects protected routes to /login when cookie is missing", () => {
    const response = middleware(request("/projects"));
    const location = response.headers.get("location");
    expect(location).toBeTruthy();
    expect(location).toContain("/login");
    expect(location).toContain("next=%2Fprojects");
  });

  it("allows protected routes when the presence cookie exists", () => {
    const response = middleware(request("/projects", "evalforge.auth=1"));
    expect(response.headers.get("location")).toBeNull();
  });
});
