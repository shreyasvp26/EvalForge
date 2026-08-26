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
  return apiRequest<GitHubConnection>(`/v1/github/connections/${connectionId}`, {
    method: "DELETE",
    token,
  });
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
