import { describe, expect, it } from "vitest";

import {
  canSubmitTaskRevision,
  githubHttpsUrl,
  isExactCommitSha,
  isGitHubNotConnectedError,
  shortSha,
} from "./repository-revision";

describe("repository-revision helpers", () => {
  it("builds github https urls", () => {
    expect(githubHttpsUrl("octocat", "Hello-World")).toBe("https://github.com/octocat/Hello-World");
  });

  it("accepts exact commit SHAs only", () => {
    expect(isExactCommitSha("abcdef0")).toBe(true);
    expect(isExactCommitSha("abcdef0123456789abcdef0123456789abcdef01")).toBe(true);
    expect(isExactCommitSha("main")).toBe(false);
    expect(isExactCommitSha("master")).toBe(false);
    expect(isExactCommitSha("latest")).toBe(false);
    expect(isExactCommitSha("")).toBe(false);
    expect(isExactCommitSha("not-hex!!!")).toBe(false);
  });

  it("requires url + exact sha before submit", () => {
    expect(
      canSubmitTaskRevision({
        repositoryUrl: "https://github.com/octocat/Hello-World",
        commitSha: "abcdef0123456789abcdef0123456789abcdef01",
      }),
    ).toBe(true);
    expect(
      canSubmitTaskRevision({
        repositoryUrl: "https://github.com/octocat/Hello-World",
        commitSha: "main",
      }),
    ).toBe(false);
    expect(
      canSubmitTaskRevision({
        repositoryUrl: "",
        commitSha: "abcdef0",
      }),
    ).toBe(false);
  });

  it("shortens sha for display", () => {
    expect(shortSha("abcdef0123456789abcdef0123456789abcdef01")).toBe("abcdef0");
  });

  it("detects github-not-connected error code for settings CTA", () => {
    expect(isGitHubNotConnectedError("GITHUB_NOT_CONNECTED")).toBe(true);
    expect(isGitHubNotConnectedError("GITHUB_UNAUTHORIZED")).toBe(false);
  });
});
