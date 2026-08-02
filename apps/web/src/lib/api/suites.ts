import type { CollectionResponse } from "@/lib/api/projects";

import { apiRequest } from "@/lib/api/client";

export type SuiteStatus = string;
export type SuiteVersionStatus = string;

export interface SuiteCompositionEntry {
  case_version_id: string;
  position: number;
  case_project_id: string;
}

export interface SuiteVersion {
  id: string;
  suite_id: string;
  version_number: number;
  status: SuiteVersionStatus;
  composition: SuiteCompositionEntry[];
  predecessor_version_id: string | null;
  created_at: string;
}

export interface Suite {
  id: string;
  project_id: string;
  name: string;
  description: string;
  status: SuiteStatus;
  created_at: string;
  active_version_id: string | null;
  versions: SuiteVersion[];
}

export interface ListSuitesParams {
  project_id: string;
  cursor?: string;
  limit?: number;
  sort?: string;
  status?: string;
  q?: string;
}

export interface CreateSuiteInput {
  project_id: string;
  name: string;
  description?: string;
}

export interface CreateSuiteDraftInput {
  composition: SuiteCompositionEntry[];
}

function buildQuery(params: ListSuitesParams): string {
  const search = new URLSearchParams();
  search.set("project_id", params.project_id);
  if (params.cursor) search.set("cursor", params.cursor);
  if (params.limit !== undefined) search.set("limit", String(params.limit));
  if (params.sort) search.set("sort", params.sort);
  if (params.status) search.set("status", params.status);
  if (params.q) search.set("q", params.q);
  return `?${search.toString()}`;
}

export async function listSuites(
  token: string,
  params: ListSuitesParams,
): Promise<CollectionResponse<Suite>> {
  return apiRequest<CollectionResponse<Suite>>(`/v1/suites${buildQuery(params)}`, {
    method: "GET",
    token,
  });
}

export async function getSuite(token: string, suiteId: string): Promise<Suite> {
  return apiRequest<Suite>(`/v1/suites/${encodeURIComponent(suiteId)}`, {
    method: "GET",
    token,
  });
}

export async function createSuite(
  token: string,
  input: CreateSuiteInput,
  idempotencyKey?: string,
): Promise<Suite> {
  const headers: Record<string, string> = {};
  if (idempotencyKey) {
    headers["Idempotency-Key"] = idempotencyKey;
  }
  return apiRequest<Suite>("/v1/suites", {
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

export async function createSuiteDraftVersion(
  token: string,
  suiteId: string,
  input: CreateSuiteDraftInput,
): Promise<SuiteVersion> {
  return apiRequest<SuiteVersion>(`/v1/suites/${encodeURIComponent(suiteId)}/versions`, {
    method: "POST",
    token,
    body: { composition: input.composition },
  });
}

export async function publishSuiteVersion(
  token: string,
  suiteId: string,
  versionId: string,
): Promise<SuiteVersion> {
  return apiRequest<SuiteVersion>(
    `/v1/suites/${encodeURIComponent(suiteId)}/versions/${encodeURIComponent(versionId)}/publish`,
    { method: "POST", token },
  );
}

export async function retireSuiteVersion(
  token: string,
  suiteId: string,
  versionId: string,
): Promise<SuiteVersion> {
  return apiRequest<SuiteVersion>(
    `/v1/suites/${encodeURIComponent(suiteId)}/versions/${encodeURIComponent(versionId)}/retire`,
    { method: "POST", token },
  );
}

export async function deprecateSuite(token: string, suiteId: string): Promise<Suite> {
  return apiRequest<Suite>(`/v1/suites/${encodeURIComponent(suiteId)}/deprecate`, {
    method: "POST",
    token,
  });
}
