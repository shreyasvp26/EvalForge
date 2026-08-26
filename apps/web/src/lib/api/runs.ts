import type { CollectionResponse } from "@/lib/api/projects";

import { ApiError, apiRequest, getApiBaseUrl } from "@/lib/api/client";

export type RunStatus = string;

export interface RunPins {
  project_id: string;
  case_version_id: string;
  prompt_version_id: string;
  agent_version_id: string;
  adapter_version_id: string;
  platform_version_id: string;
  grader_version_ids: string[];
  suite_version_id: string | null;
}

export interface ScoreValue {
  numeric: number | null;
  categorical: string | null;
  passed: boolean | null;
  detail?: Record<string, unknown>;
}

export interface Score {
  id: string;
  grader_id: string;
  grader_version_id: string;
  value: ScoreValue;
  explanation_artifact_id: string | null;
}

export interface Run {
  id: string;
  status: RunStatus;
  created_at: string;
  pins: RunPins;
  failure_reason: string | null;
  failure_category: string | null;
  cancellation_reason: string | null;
  sandbox_id: string | null;
  expected_grader_count: number;
  produced_score_count: number;
  is_partially_graded: boolean;
  scores: Score[];
  telemetry?: RunTelemetry | null;
  execution_mode?: string | null;
  execution_metadata?: Record<string, string>;
  runtime_request?: Record<string, string>;
  execution_group_id?: string | null;
  publication?: {
    status?: string;
    branch_name?: string;
    base_commit_sha?: string;
    result_commit_sha?: string;
    pull_request_url?: string;
    pull_request_number?: number;
    repository_url?: string;
    error_code?: string;
    error_message?: string;
  };
}

export interface RunTelemetry {
  wall_clock_ms: number | null;
  compute_ms: number | null;
  input_tokens: number | null;
  output_tokens: number | null;
  total_tokens: number | null;
  estimated_cost: null;
  provider_usage_available: boolean;
}

export interface ExecutionEvent {
  id: string;
  run_id: string;
  sequence: number;
  kind: string;
  action: Record<string, unknown>;
  artifact_ids: string[];
  occurred_at: string;
  metadata: Record<string, string>;
}

export interface Artifact {
  id: string;
  run_id: string;
  kind: string;
  storage_key: string;
  content_type: string;
  size_bytes: number;
  checksum: string;
  created_at: string;
  produced_by_grader_version_id: string | null;
}

export interface GraderVersionRef {
  grader_id: string;
  grader_version_id: string;
}

export interface ListRunsParams {
  project_id: string;
  cursor?: string;
  limit?: number;
  sort?: string;
  status?: string;
}

export interface CreateRunInput {
  project_id: string;
  case_id: string;
  case_version_id: string;
  prompt_version_id: string;
  agent_id: string;
  agent_version_id: string;
  adapter_version_id: string;
  grader_version_refs: GraderVersionRef[];
  platform_version_id: string;
  suite_id?: string | null;
  suite_version_id?: string | null;
  provider_key?: string | null;
  gateway_key?: string | null;
  model_id?: string | null;
  routing_mode?: string | null;
  provider_connection_id?: string | null;
  credential_ref_id?: string | null;
}

export interface CancelRunInput {
  reason?: string | null;
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

export async function listRuns(
  token: string,
  params: ListRunsParams,
): Promise<CollectionResponse<Run>> {
  return apiRequest<CollectionResponse<Run>>(
    `/v1/runs${buildQuery({
      project_id: params.project_id,
      cursor: params.cursor,
      limit: params.limit,
      sort: params.sort,
      status: params.status,
    })}`,
    { method: "GET", token },
  );
}

export async function getRun(token: string, runId: string): Promise<Run> {
  return apiRequest<Run>(`/v1/runs/${encodeURIComponent(runId)}`, {
    method: "GET",
    token,
  });
}

export async function createRun(
  token: string,
  input: CreateRunInput,
  idempotencyKey?: string,
): Promise<Run> {
  const headers: Record<string, string> = {};
  if (idempotencyKey) {
    headers["Idempotency-Key"] = idempotencyKey;
  }
  return apiRequest<Run>("/v1/runs", {
    method: "POST",
    token,
    headers,
    body: {
      project_id: input.project_id,
      case_id: input.case_id,
      case_version_id: input.case_version_id,
      prompt_version_id: input.prompt_version_id,
      agent_id: input.agent_id,
      agent_version_id: input.agent_version_id,
      adapter_version_id: input.adapter_version_id,
      grader_version_refs: input.grader_version_refs,
      platform_version_id: input.platform_version_id,
      suite_id: input.suite_id ?? null,
      suite_version_id: input.suite_version_id ?? null,
      provider_key: input.provider_key ?? null,
      gateway_key: input.gateway_key ?? null,
      model_id: input.model_id ?? null,
      routing_mode: input.routing_mode ?? null,
      provider_connection_id: input.provider_connection_id ?? null,
      credential_ref_id: input.credential_ref_id ?? null,
    },
  });
}

export async function cancelRun(
  token: string,
  runId: string,
  input?: CancelRunInput,
): Promise<Run> {
  return apiRequest<Run>(`/v1/runs/${encodeURIComponent(runId)}/cancel`, {
    method: "POST",
    token,
    body: { reason: input?.reason ?? null },
  });
}

export async function listRunEvents(
  token: string,
  runId: string,
  params?: { limit?: number; sort?: string },
): Promise<CollectionResponse<ExecutionEvent>> {
  return apiRequest<CollectionResponse<ExecutionEvent>>(
    `/v1/runs/${encodeURIComponent(runId)}/events${buildQuery({
      limit: params?.limit,
      sort: params?.sort,
    })}`,
    { method: "GET", token },
  );
}

export async function listRunArtifacts(
  token: string,
  runId: string,
  params?: { limit?: number; sort?: string },
): Promise<CollectionResponse<Artifact>> {
  return apiRequest<CollectionResponse<Artifact>>(
    `/v1/runs/${encodeURIComponent(runId)}/artifacts${buildQuery({
      limit: params?.limit,
      sort: params?.sort,
    })}`,
    { method: "GET", token },
  );
}

export async function listRunScores(
  token: string,
  runId: string,
  params?: { limit?: number },
): Promise<CollectionResponse<Score>> {
  return apiRequest<CollectionResponse<Score>>(
    `/v1/runs/${encodeURIComponent(runId)}/scores${buildQuery({
      limit: params?.limit,
    })}`,
    { method: "GET", token },
  );
}

export interface ScoreAggregate {
  passed: boolean | null;
  overall_score: number | null;
  objective_failed: boolean;
  score_count: number;
  reason: string;
}

export interface Reproducibility {
  can_reproduce: boolean;
  missing: string[];
  notes: string;
}

export interface RunProvenance {
  run_id: string;
  status: string;
  created_at: string;
  failure_reason: string | null;
  failure_category: string | null;
  cancellation_reason: string | null;
  project_id: string;
  case_version_id: string;
  prompt_version_id: string;
  agent_version_id: string;
  adapter_version_id: string;
  platform_version_id: string;
  grader_version_ids: string[];
  suite_version_id: string | null;
  repository_url: string | null;
  commit_sha: string | null;
  subdirectory: string | null;
  agent_name: string | null;
  agent_version_label: string | null;
  adapter_name: string | null;
  adapter_version_label: string | null;
  adapter_key: string | null;
  grader_summaries: Record<string, unknown>[];
  score_aggregate: ScoreAggregate;
  expected_grader_count: number;
  produced_score_count: number;
  is_partially_graded: boolean;
  telemetry: RunTelemetry;
  event_count: number;
  artifact_count: number;
  execution_mode: string | null;
  execution_metadata: Record<string, string>;
  platform_name?: string | null;
  platform_version_label?: string | null;
  platform_policy_summaries?: Record<string, Record<string, string>>;
  benchmark_key?: string | null;
  suite_version_id_as_benchmark?: string | null;
  provider_key?: string | null;
  gateway_key?: string | null;
  requested_model?: string | null;
  actual_model?: string | null;
  routing_mode?: string | null;
  canonical_evaluation?: boolean | null;
  credential_ref_id?: string | null;
  fallback_used?: boolean | null;
  reproducibility: Reproducibility;
}

export interface RunComparisonEntry {
  run_id: string;
  status: string;
  failure_reason: string | null;
  failure_category: string | null;
  pins: RunPins;
  repository_url: string | null;
  commit_sha: string | null;
  adapter_key: string | null;
  adapter_name: string | null;
  prompt_version: string | null;
  agent_version: string | null;
  telemetry: RunTelemetry;
  score_aggregate: ScoreAggregate;
  duration_ms: number | null;
  execution_mode?: string | null;
  benchmark_key?: string | null;
  suite_version_id?: string | null;
  provider_key?: string | null;
  gateway_key?: string | null;
  requested_model?: string | null;
  routing_mode?: string | null;
  canonical_evaluation?: boolean | null;
}

export interface RunComparisonDelta {
  run_id: string;
  score_delta: number | null;
  pass_changed: boolean | null;
  duration_delta_ms: number | null;
  pin_differences: string[];
}

export interface RunComparability {
  compatible: boolean;
  shared_dimensions: string[];
  agent_difference_dimensions: string[];
  mismatches: string[];
  expected_agent_differences: string[];
  benchmark_key: string | null;
  notes: string;
}

export interface RunComparisonResult {
  baseline_run_id: string;
  runs: RunComparisonEntry[];
  deltas: RunComparisonDelta[];
  comparability: RunComparability;
}

export interface FailingGraderReason {
  grader_id: string;
  grader_version_id: string;
  reason: string;
}

export interface RunDiagnosis {
  run_id: string;
  status: string;
  summary: string;
  category: string | null;
  reason: string | null;
  evidence: string[];
  failing_grader_reasons: FailingGraderReason[];
  last_events: ExecutionEvent[];
  relevant_artifact_ids: string[];
}

export interface ArtifactPreview {
  artifact_id: string;
  content_type: string;
  size_bytes: number;
  preview: string | null;
  truncated: boolean;
  previewable: boolean;
}

export async function getRunProvenance(token: string, runId: string): Promise<RunProvenance> {
  return apiRequest<RunProvenance>(`/v1/runs/${encodeURIComponent(runId)}/provenance`, {
    method: "GET",
    token,
  });
}

export async function compareRuns(token: string, runIds: string[]): Promise<RunComparisonResult> {
  return apiRequest<RunComparisonResult>("/v1/runs/compare", {
    method: "POST",
    token,
    body: { run_ids: runIds },
  });
}

export async function diagnoseRunFailure(token: string, runId: string): Promise<RunDiagnosis> {
  return apiRequest<RunDiagnosis>(`/v1/runs/${encodeURIComponent(runId)}/diagnosis`, {
    method: "GET",
    token,
  });
}

export async function previewRunArtifact(
  token: string,
  runId: string,
  artifactId: string,
): Promise<ArtifactPreview> {
  return apiRequest<ArtifactPreview>(
    `/v1/runs/${encodeURIComponent(runId)}/artifacts/${encodeURIComponent(artifactId)}/preview`,
    { method: "GET", token },
  );
}

/** Absolute URL for downloading artifact bytes (requires Authorization header). */
export function runArtifactContentPath(runId: string, artifactId: string): string {
  return `/v1/runs/${encodeURIComponent(runId)}/artifacts/${encodeURIComponent(artifactId)}/content`;
}

export async function downloadRunArtifact(
  token: string,
  runId: string,
  artifactId: string,
): Promise<{ blob: Blob; contentType: string; checksum: string | null }> {
  const response = await fetch(`${getApiBaseUrl()}${runArtifactContentPath(runId, artifactId)}`, {
    method: "GET",
    headers: {
      Accept: "*/*",
      Authorization: `Bearer ${token}`,
    },
    cache: "no-store",
  });
  if (!response.ok) {
    let message = `Download failed (${String(response.status)})`;
    let code = "download_failed";
    try {
      const body = (await response.json()) as { error?: { message?: string; code?: string } };
      if (body.error?.message) message = body.error.message;
      if (body.error?.code) code = body.error.code;
    } catch {
      // non-JSON error body
    }
    throw new ApiError(message, {
      status: response.status,
      code,
      retryable: response.status >= 500,
    });
  }
  const blob = await response.blob();
  return {
    blob,
    contentType: response.headers.get("Content-Type") ?? "application/octet-stream",
    checksum: response.headers.get("X-EvalForge-Checksum"),
  };
}
