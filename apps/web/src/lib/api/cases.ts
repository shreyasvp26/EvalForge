import type { CollectionResponse } from "@/lib/api/projects";

import { apiRequest } from "@/lib/api/client";

export type CaseStatus = string;
export type CaseVersionStatus = string;
export type PromptVersionStatus = string;

export interface PromptVersion {
  id: string;
  prompt_id: string;
  version_number: number;
  status: PromptVersionStatus;
  content: string;
  predecessor_version_id: string | null;
  created_at: string;
}

export interface CaseVersion {
  id: string;
  case_id: string;
  version_number: number;
  status: CaseVersionStatus;
  description: string;
  repository_url: string;
  commit_sha: string;
  subdirectory: string | null;
  expected_checks: string[];
  applicable_grader_ids: string[];
  prompt_version_id: string;
  predecessor_version_id: string | null;
  created_at: string;
}

export interface Case {
  id: string;
  project_id: string;
  prompt_id: string;
  name: string;
  description: string;
  status: CaseStatus;
  created_at: string;
  active_version_id: string | null;
  active_prompt_version_id: string | null;
  versions: CaseVersion[];
  prompt_versions: PromptVersion[];
}

export interface ListCasesParams {
  project_id: string;
  cursor?: string;
  limit?: number;
  sort?: string;
  status?: string;
  q?: string;
}

export interface CreateCaseInput {
  project_id: string;
  name: string;
  description?: string;
}

export interface CreatePromptDraftInput {
  content: string;
}

export interface CreateCaseDraftInput {
  description: string;
  repository_url: string;
  commit_sha: string;
  expected_checks?: string[];
  applicable_grader_ids?: string[];
  prompt_version_id: string;
  subdirectory?: string | null;
}

function buildQuery(params: ListCasesParams): string {
  const search = new URLSearchParams();
  search.set("project_id", params.project_id);
  if (params.cursor) search.set("cursor", params.cursor);
  if (params.limit !== undefined) search.set("limit", String(params.limit));
  if (params.sort) search.set("sort", params.sort);
  if (params.status) search.set("status", params.status);
  if (params.q) search.set("q", params.q);
  return `?${search.toString()}`;
}

export async function listCases(
  token: string,
  params: ListCasesParams,
): Promise<CollectionResponse<Case>> {
  return apiRequest<CollectionResponse<Case>>(`/v1/cases${buildQuery(params)}`, {
    method: "GET",
    token,
  });
}

export async function getCase(token: string, caseId: string): Promise<Case> {
  return apiRequest<Case>(`/v1/cases/${encodeURIComponent(caseId)}`, {
    method: "GET",
    token,
  });
}

export async function createCase(
  token: string,
  input: CreateCaseInput,
  idempotencyKey?: string,
): Promise<Case> {
  const headers: Record<string, string> = {};
  if (idempotencyKey) {
    headers["Idempotency-Key"] = idempotencyKey;
  }
  return apiRequest<Case>("/v1/cases", {
    method: "POST",
    token,
    headers,
    body: {
      project_id: input.project_id,
      name: input.name,
      description: input.description ?? "",
    },
  });
}

export async function createPromptDraftVersion(
  token: string,
  caseId: string,
  input: CreatePromptDraftInput,
): Promise<PromptVersion> {
  return apiRequest<PromptVersion>(`/v1/cases/${encodeURIComponent(caseId)}/prompts/versions`, {
    method: "POST",
    token,
    body: { content: input.content },
  });
}

export async function publishPromptVersion(
  token: string,
  caseId: string,
  versionId: string,
): Promise<PromptVersion> {
  return apiRequest<PromptVersion>(
    `/v1/cases/${encodeURIComponent(caseId)}/prompts/versions/${encodeURIComponent(versionId)}/publish`,
    { method: "POST", token },
  );
}

export async function createCaseDraftVersion(
  token: string,
  caseId: string,
  input: CreateCaseDraftInput,
): Promise<CaseVersion> {
  return apiRequest<CaseVersion>(`/v1/cases/${encodeURIComponent(caseId)}/versions`, {
    method: "POST",
    token,
    body: {
      description: input.description,
      repository_url: input.repository_url,
      commit_sha: input.commit_sha,
      expected_checks: input.expected_checks ?? [],
      applicable_grader_ids: input.applicable_grader_ids ?? [],
      prompt_version_id: input.prompt_version_id,
      subdirectory: input.subdirectory ?? null,
    },
  });
}

export async function publishCaseVersion(
  token: string,
  caseId: string,
  versionId: string,
): Promise<CaseVersion> {
  return apiRequest<CaseVersion>(
    `/v1/cases/${encodeURIComponent(caseId)}/versions/${encodeURIComponent(versionId)}/publish`,
    { method: "POST", token },
  );
}

export async function deprecateCase(token: string, caseId: string): Promise<Case> {
  return apiRequest<Case>(`/v1/cases/${encodeURIComponent(caseId)}/deprecate`, {
    method: "POST",
    token,
  });
}
