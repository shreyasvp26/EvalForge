import type { CollectionResponse } from "@/lib/api/projects";

import { apiRequest } from "@/lib/api/client";

export interface GitHubConnection {
  id: string;
  display_name: string;
  status: string;
  scopes: string[];
  github_login: string | null;
  masked_token: string;
  key_fingerprint: string;
  created_at: string;
  metadata: Record<string, string>;
}

export interface GitHubRepoSummary {
  owner: string;
  name: string;
  full_name: string;
  default_branch: string;
  private: boolean;
  html_url: string;
  description: string | null;
}

export interface GitHubBranch {
  name: string;
  protected: boolean;
}

export interface GitHubCommit {
  sha: string;
  short_sha: string;
  message: string;
  committed_at: string | null;
  html_url: string | null;
  repository_url: string;
  branch: string;
}

export interface PublicationResult {
  eligibility: {
    eligible: boolean;
    reason: string;
    evaluation_passed: boolean | null;
    run_status: string;
    score_count: number;
  };
  publication: Record<string, unknown>;
  run: Record<string, unknown>;
}

function buildQuery(params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === "") continue;
    search.set(key, String(value));
  }
  const query = search.toString();
  return query ? `?${query}` : "";
}

export async function listGitHubConnections(
  token: string,
): Promise<CollectionResponse<GitHubConnection>> {
  // API returns a bare list (not a cursor page); normalize for shared CollectionResponse.
  const items = await apiRequest<GitHubConnection[]>("/v1/github/connections", { token });
  return {
    items,
    count: items.length,
    next_cursor: null,
    has_more: false,
  };
}

export async function createGitHubConnection(
  token: string,
  body: { token: string; display_name?: string; scopes?: string[]; github_login?: string },
): Promise<GitHubConnection> {
  return apiRequest<GitHubConnection>("/v1/github/connections", {
    method: "POST",
    token,
    body,
  });
}

export async function revokeGitHubConnection(
  token: string,
  connectionId: string,
): Promise<GitHubConnection> {
  return apiRequest<GitHubConnection>(
    `/v1/github/connections/${encodeURIComponent(connectionId)}`,
    {
      method: "DELETE",
      token,
    },
  );
}

export async function listGitHubRepositories(
  token: string,
  params?: { connection_id?: string; limit?: number },
): Promise<CollectionResponse<GitHubRepoSummary>> {
  return apiRequest<CollectionResponse<GitHubRepoSummary>>(
    `/v1/github/repositories${buildQuery({
      connection_id: params?.connection_id,
      limit: params?.limit,
    })}`,
    { method: "GET", token },
  );
}

export async function listGitHubBranches(
  token: string,
  owner: string,
  repo: string,
  params?: { connection_id?: string; limit?: number },
): Promise<CollectionResponse<GitHubBranch>> {
  return apiRequest<CollectionResponse<GitHubBranch>>(
    `/v1/github/repositories/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}/branches${buildQuery(
      {
        connection_id: params?.connection_id,
        limit: params?.limit,
      },
    )}`,
    { method: "GET", token },
  );
}

export async function getGitHubBranchHead(
  token: string,
  owner: string,
  repo: string,
  branch: string,
  params?: { connection_id?: string },
): Promise<GitHubCommit> {
  return apiRequest<GitHubCommit>(
    `/v1/github/repositories/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}/commits/${encodeURIComponent(branch)}${buildQuery(
      { connection_id: params?.connection_id },
    )}`,
    { method: "GET", token },
  );
}

export async function publishRun(
  token: string,
  runId: string,
  body?: { github_connection_id?: string; base_branch?: string },
): Promise<PublicationResult> {
  return apiRequest<PublicationResult>(`/v1/runs/${runId}/publish`, {
    method: "POST",
    token,
    body: body ?? {},
  });
}
