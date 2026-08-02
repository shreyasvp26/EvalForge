import { apiRequest } from "@/lib/api/client";

export type ProjectStatus = string;

export interface Project {
  id: string;
  name: string;
  description: string;
  status: ProjectStatus;
  created_at: string;
  settings: Record<string, string>;
}

export interface CollectionResponse<T> {
  items: T[];
  count: number;
  next_cursor: string | null;
  has_more: boolean;
}

export interface ListProjectsParams {
  cursor?: string;
  limit?: number;
  sort?: string;
  status?: string;
  q?: string;
}

export interface CreateProjectInput {
  name: string;
  description?: string;
  settings?: Record<string, string>;
}

function buildQuery(params: ListProjectsParams = {}): string {
  const search = new URLSearchParams();
  if (params.cursor) search.set("cursor", params.cursor);
  if (params.limit !== undefined) search.set("limit", String(params.limit));
  if (params.sort) search.set("sort", params.sort);
  if (params.status) search.set("status", params.status);
  if (params.q) search.set("q", params.q);
  const query = search.toString();
  return query ? `?${query}` : "";
}

export async function listProjects(
  token: string,
  params?: ListProjectsParams,
): Promise<CollectionResponse<Project>> {
  return apiRequest<CollectionResponse<Project>>(`/v1/projects${buildQuery(params)}`, {
    method: "GET",
    token,
  });
}

export async function getProject(token: string, projectId: string): Promise<Project> {
  return apiRequest<Project>(`/v1/projects/${encodeURIComponent(projectId)}`, {
    method: "GET",
    token,
  });
}

export async function createProject(
  token: string,
  input: CreateProjectInput,
  idempotencyKey?: string,
): Promise<Project> {
  const headers: Record<string, string> = {};
  if (idempotencyKey) {
    headers["Idempotency-Key"] = idempotencyKey;
  }
  return apiRequest<Project>("/v1/projects", {
    method: "POST",
    token,
    headers,
    body: {
      name: input.name,
      description: input.description ?? "",
      settings: input.settings ?? {},
    },
  });
}

export async function renameProject(
  token: string,
  projectId: string,
  name: string,
): Promise<Project> {
  return apiRequest<Project>(`/v1/projects/${encodeURIComponent(projectId)}`, {
    method: "PATCH",
    token,
    body: { name },
  });
}

export async function updateProjectSettings(
  token: string,
  projectId: string,
  settings: Record<string, string>,
): Promise<Project> {
  return apiRequest<Project>(`/v1/projects/${encodeURIComponent(projectId)}/settings`, {
    method: "PATCH",
    token,
    body: { settings },
  });
}

export async function deprecateProject(token: string, projectId: string): Promise<Project> {
  return apiRequest<Project>(`/v1/projects/${encodeURIComponent(projectId)}/deprecate`, {
    method: "POST",
    token,
  });
}
