/** Pure helpers for GitHub repository → exact SHA task revision selection. */

const COMMIT_SHA_RE = /^[0-9a-fA-F]{7,40}$/;

const FORBIDDEN_REVISION_NAMES = new Set([
  "main",
  "master",
  "latest",
  "head",
  "origin/main",
  "origin/master",
]);

export function githubHttpsUrl(owner: string, repo: string): string {
  return `https://github.com/${owner.trim()}/${repo.trim()}`;
}

export function isExactCommitSha(value: string): boolean {
  const sha = value.trim();
  if (!sha) return false;
  if (FORBIDDEN_REVISION_NAMES.has(sha.toLowerCase())) return false;
  return COMMIT_SHA_RE.test(sha);
}

export function canSubmitTaskRevision(input: {
  repositoryUrl: string;
  commitSha: string;
}): boolean {
  return Boolean(input.repositoryUrl.trim()) && isExactCommitSha(input.commitSha);
}

export function shortSha(sha: string): string {
  const cleaned = sha.trim();
  return cleaned.length >= 7 ? cleaned.slice(0, 7) : cleaned;
}

export function isGitHubNotConnectedError(code: string | undefined): boolean {
  return code === "GITHUB_NOT_CONNECTED";
}
