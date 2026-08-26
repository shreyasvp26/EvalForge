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
  catalog_key?: string;
  catalog_visible?: boolean;
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

export interface ExecuteSuiteInput {
  agent_id: string;
  agent_version_id: string;
  adapter_version_id: string;
  platform_version_id: string;
  execution_group_id?: string;
}

export interface SuiteExecution {
  suite_id: string;
  suite_version_id: string;
  execution_group_id: string;
  total_cases: number;
  runs: {
    case_version_id: string;
    position: number;
    run: { id: string; status: string };
  }[];
}

export interface SuiteAggregate {
  suite_id: string;
  suite_version_id: string;
  execution_group_id: string | null;
  total_cases: number;
  run_count: number;
  completed: number;
  failed: number;
  execution_failed: number;
  cancelled: number;
  queued_or_running: number;
  passed: number;
  evaluation_failed: number;
  objective_failed_count: number;
  pass_rate: number | null;
  average_score: number | null;
  cases: {
    case_version_id: string;
    run_id: string;
    status: string;
    aggregate: {
      passed: boolean | null;
      overall_score: number | null;
      objective_failed: boolean;
      score_count: number;
      reason: string;
    };
    failure_reason: string | null;
    failure_category: string | null;
  }[];
}

export async function executeSuiteVersion(
  token: string,
  suiteId: string,
  versionId: string,
  input: ExecuteSuiteInput,
  idempotencyKey?: string,
): Promise<SuiteExecution> {
  const headers: Record<string, string> = {};
  if (idempotencyKey) {
    headers["Idempotency-Key"] = idempotencyKey;
  }
  return apiRequest<SuiteExecution>(
    `/v1/suites/${encodeURIComponent(suiteId)}/versions/${encodeURIComponent(versionId)}/execute`,
    {
      method: "POST",
      token,
      headers,
      body: input,
    },
  );
}

export async function getSuiteVersionResults(
  token: string,
  suiteId: string,
  versionId: string,
  executionGroupId?: string,
): Promise<SuiteAggregate> {
  const search = new URLSearchParams();
  if (executionGroupId) search.set("execution_group_id", executionGroupId);
  const qs = search.toString();
  return apiRequest<SuiteAggregate>(
    `/v1/suites/${encodeURIComponent(suiteId)}/versions/${encodeURIComponent(versionId)}/results${qs ? `?${qs}` : ""}`,
    { method: "GET", token },
  );
}
