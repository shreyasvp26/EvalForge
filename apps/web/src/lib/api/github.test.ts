import { afterEach, describe, expect, it, vi } from "vitest";

import { getGitHubBranchHead, listGitHubBranches, listGitHubRepositories } from "@/lib/api/github";

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("github repository API client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("lists repositories without leaking tokens in the path", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse(200, {
        items: [
          {
            owner: "octocat",
            name: "Hello-World",
            full_name: "octocat/Hello-World",
            default_branch: "main",
            private: false,
            html_url: "https://github.com/octocat/Hello-World",
            description: null,
          },
        ],
        count: 1,
        next_cursor: null,
        has_more: false,
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await listGitHubRepositories("session-token", { limit: 50 });
    expect(result.items[0]?.full_name).toBe("octocat/Hello-World");
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/v1/github/repositories");
    expect(url).toContain("limit=50");
    expect(url).not.toContain("session-token");
    expect(url).not.toContain("ghp_");
    const headers = new Headers(init.headers);
    expect(headers.get("Authorization")).toBe("Bearer session-token");
  });

  it("loads branches after repository selection", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse(200, {
        items: [
          { name: "main", protected: true },
          { name: "develop", protected: false },
        ],
        count: 2,
        next_cursor: null,
        has_more: false,
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await listGitHubBranches("session-token", "octocat", "Hello-World");
    expect(result.items.map((b) => b.name)).toEqual(["main", "develop"]);
    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url).toContain("/v1/github/repositories/octocat/Hello-World/branches");
  });

  it("resolves branch head to an exact sha (not the branch name)", async () => {
    const sha = "abcdef0123456789abcdef0123456789abcdef01";
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse(200, {
        sha,
        short_sha: "abcdef0",
        message: "Initial",
        committed_at: "2026-08-26T00:00:00Z",
        html_url: `https://github.com/octocat/Hello-World/commit/${sha}`,
        repository_url: "https://github.com/octocat/Hello-World",
        branch: "main",
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await getGitHubBranchHead("session-token", "octocat", "Hello-World", "main");
    expect(result.sha).toBe(sha);
    expect(result.sha).not.toBe("main");
    expect(result.branch).toBe("main");
    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url).toContain("/v1/github/repositories/octocat/Hello-World/commits/main");
  });

  it("surfaces github-not-connected API failures", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse(422, {
        error: {
          code: "GITHUB_NOT_CONNECTED",
          message: "Connect GitHub in Settings to select a repository.",
          retryable: false,
        },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(listGitHubRepositories("session-token")).rejects.toMatchObject({
      code: "GITHUB_NOT_CONNECTED",
      message: "Connect GitHub in Settings to select a repository.",
    });
  });
});
