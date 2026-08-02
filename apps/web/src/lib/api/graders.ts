import type { CollectionResponse } from "@/lib/api/projects";

import { apiRequest } from "@/lib/api/client";

export type GraderStatus = string;
export type GraderVersionStatus = string;
export type GraderFamily = string;

export interface GraderVersion {
  id: string;
  grader_id: string;
  version_number: number;
  status: GraderVersionStatus;
  label: string;
  specification: string;
  predecessor_version_id: string | null;
  created_at: string;
}

export interface Grader {
  id: string;
  name: string;
  family: GraderFamily;
  description: string;
  status: GraderStatus;
  created_at: string;
  active_version_id: string | null;
  versions: GraderVersion[];
}

export interface ListGradersParams {
  cursor?: string;
  limit?: number;
  sort?: string;
  status?: string;
  q?: string;
}

export interface CreateGraderInput {
  name: string;
  family: string;
  description?: string;
}

export interface CreateGraderDraftInput {
  label: string;
  specification: string;
}

function buildQuery(params: ListGradersParams = {}): string {
  const search = new URLSearchParams();
  if (params.cursor) search.set("cursor", params.cursor);
  if (params.limit !== undefined) search.set("limit", String(params.limit));
  if (params.sort) search.set("sort", params.sort);
  if (params.status) search.set("status", params.status);
  if (params.q) search.set("q", params.q);
  const query = search.toString();
  return query ? `?${query}` : "";
}

export async function listGraders(
  token: string,
  params?: ListGradersParams,
): Promise<CollectionResponse<Grader>> {
  return apiRequest<CollectionResponse<Grader>>(`/v1/graders${buildQuery(params)}`, {
    method: "GET",
    token,
  });
}

export async function getGrader(token: string, graderId: string): Promise<Grader> {
  return apiRequest<Grader>(`/v1/graders/${encodeURIComponent(graderId)}`, {
    method: "GET",
    token,
  });
}

export async function createGrader(
  token: string,
  input: CreateGraderInput,
  idempotencyKey?: string,
): Promise<Grader> {
  const headers: Record<string, string> = {};
  if (idempotencyKey) {
    headers["Idempotency-Key"] = idempotencyKey;
  }
  return apiRequest<Grader>("/v1/graders", {
    method: "POST",
    token,
    headers,
    body: {
      name: input.name,
      family: input.family,
      description: input.description ?? "",
    },
  });
}

export async function createGraderDraftVersion(
  token: string,
  graderId: string,
  input: CreateGraderDraftInput,
): Promise<GraderVersion> {
  return apiRequest<GraderVersion>(`/v1/graders/${encodeURIComponent(graderId)}/versions`, {
    method: "POST",
    token,
    body: {
      label: input.label,
      specification: input.specification,
    },
  });
}

export async function publishGraderVersion(
  token: string,
  graderId: string,
  versionId: string,
): Promise<GraderVersion> {
  return apiRequest<GraderVersion>(
    `/v1/graders/${encodeURIComponent(graderId)}/versions/${encodeURIComponent(versionId)}/publish`,
    { method: "POST", token },
  );
}
