import type { CollectionResponse } from "@/lib/api/projects";
import type { Suite, SuiteAggregate, SuiteExecution, ExecuteSuiteInput } from "@/lib/api/suites";

import { apiRequest } from "@/lib/api/client";

export interface BenchmarkCatalogEntry {
  suite_id: string;
  project_id: string;
  catalog_key: string;
  name: string;
  description: string;
  status: string;
  active_version_id: string | null;
  active_version_number: number | null;
  case_count: number;
  categories: string[];
  difficulties: string[];
  created_at: string;
  catalog_visible: boolean;
}

export async function listBenchmarks(
  token: string,
  projectId: string,
): Promise<CollectionResponse<BenchmarkCatalogEntry>> {
  const search = new URLSearchParams({ project_id: projectId });
  return apiRequest<CollectionResponse<BenchmarkCatalogEntry>>(
    `/v1/benchmarks?${search.toString()}`,
    { method: "GET", token },
  );
}

export async function getBenchmark(token: string, suiteId: string): Promise<Suite> {
  return apiRequest<Suite>(`/v1/benchmarks/${encodeURIComponent(suiteId)}`, {
    method: "GET",
    token,
  });
}

export async function executeBenchmark(
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
    `/v1/benchmarks/${encodeURIComponent(suiteId)}/versions/${encodeURIComponent(versionId)}/execute`,
    {
      method: "POST",
      token,
      headers,
      body: input,
    },
  );
}

export async function getBenchmarkResults(
  token: string,
  suiteId: string,
  versionId: string,
  executionGroupId?: string,
): Promise<SuiteAggregate> {
  const search = new URLSearchParams();
  if (executionGroupId) search.set("execution_group_id", executionGroupId);
  const qs = search.toString();
  return apiRequest<SuiteAggregate>(
    `/v1/benchmarks/${encodeURIComponent(suiteId)}/versions/${encodeURIComponent(versionId)}/results${qs ? `?${qs}` : ""}`,
    { method: "GET", token },
  );
}
