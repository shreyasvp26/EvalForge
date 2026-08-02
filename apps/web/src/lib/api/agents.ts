import type { CollectionResponse } from "@/lib/api/projects";

import { apiRequest } from "@/lib/api/client";

export type AgentStatus = string;
export type AgentVersionStatus = string;
export type AdapterStatus = string;
export type AdapterVersionStatus = string;

export interface AgentVersion {
  id: string;
  agent_id: string;
  version_number: number;
  status: AgentVersionStatus;
  label: string;
  release_notes: string;
  predecessor_version_id: string | null;
  created_at: string;
}

export interface Agent {
  id: string;
  name: string;
  description: string;
  adapter_id: string | null;
  status: AgentStatus;
  created_at: string;
  active_version_id: string | null;
  versions: AgentVersion[];
}

export interface AdapterVersion {
  id: string;
  adapter_id: string;
  version_number: number;
  status: AdapterVersionStatus;
  label: string;
  notes: string;
  predecessor_version_id: string | null;
  created_at: string;
}

export interface Adapter {
  id: string;
  agent_id: string;
  name: string;
  status: AdapterStatus;
  created_at: string;
  active_version_id: string | null;
  versions: AdapterVersion[];
}

export interface ListAgentsParams {
  cursor?: string;
  limit?: number;
  sort?: string;
  status?: string;
  q?: string;
}

export interface ListAdaptersParams {
  cursor?: string;
  limit?: number;
  sort?: string;
  status?: string;
  q?: string;
}

export interface CreateAgentInput {
  name: string;
  description?: string;
}

export interface CreateAgentDraftInput {
  label: string;
  release_notes?: string;
}

export interface CreateAdapterInput {
  agent_id: string;
  name: string;
}

export interface CreateAdapterDraftInput {
  label: string;
  notes?: string;
}

function buildQuery(params: ListAgentsParams | ListAdaptersParams = {}): string {
  const search = new URLSearchParams();
  if (params.cursor) search.set("cursor", params.cursor);
  if (params.limit !== undefined) search.set("limit", String(params.limit));
  if (params.sort) search.set("sort", params.sort);
  if (params.status) search.set("status", params.status);
  if (params.q) search.set("q", params.q);
  const query = search.toString();
  return query ? `?${query}` : "";
}

export async function listAgents(
  token: string,
  params?: ListAgentsParams,
): Promise<CollectionResponse<Agent>> {
  return apiRequest<CollectionResponse<Agent>>(`/v1/agents${buildQuery(params)}`, {
    method: "GET",
    token,
  });
}

export async function getAgent(token: string, agentId: string): Promise<Agent> {
  return apiRequest<Agent>(`/v1/agents/${encodeURIComponent(agentId)}`, {
    method: "GET",
    token,
  });
}

export async function createAgent(
  token: string,
  input: CreateAgentInput,
  idempotencyKey?: string,
): Promise<Agent> {
  const headers: Record<string, string> = {};
  if (idempotencyKey) {
    headers["Idempotency-Key"] = idempotencyKey;
  }
  return apiRequest<Agent>("/v1/agents", {
    method: "POST",
    token,
    headers,
    body: {
      name: input.name,
      description: input.description ?? "",
    },
  });
}

export async function createAgentDraftVersion(
  token: string,
  agentId: string,
  input: CreateAgentDraftInput,
): Promise<AgentVersion> {
  return apiRequest<AgentVersion>(`/v1/agents/${encodeURIComponent(agentId)}/versions`, {
    method: "POST",
    token,
    body: {
      label: input.label,
      release_notes: input.release_notes ?? "",
    },
  });
}

export async function publishAgentVersion(
  token: string,
  agentId: string,
  versionId: string,
): Promise<AgentVersion> {
  return apiRequest<AgentVersion>(
    `/v1/agents/${encodeURIComponent(agentId)}/versions/${encodeURIComponent(versionId)}/publish`,
    { method: "POST", token },
  );
}

export async function listAdapters(
  token: string,
  params?: ListAdaptersParams,
): Promise<CollectionResponse<Adapter>> {
  return apiRequest<CollectionResponse<Adapter>>(`/v1/adapters${buildQuery(params)}`, {
    method: "GET",
    token,
  });
}

export async function getAdapter(token: string, adapterId: string): Promise<Adapter> {
  return apiRequest<Adapter>(`/v1/adapters/${encodeURIComponent(adapterId)}`, {
    method: "GET",
    token,
  });
}

export async function createAdapter(
  token: string,
  input: CreateAdapterInput,
  idempotencyKey?: string,
): Promise<Adapter> {
  const headers: Record<string, string> = {};
  if (idempotencyKey) {
    headers["Idempotency-Key"] = idempotencyKey;
  }
  return apiRequest<Adapter>("/v1/adapters", {
    method: "POST",
    token,
    headers,
    body: {
      agent_id: input.agent_id,
      name: input.name,
    },
  });
}

export async function createAdapterDraftVersion(
  token: string,
  adapterId: string,
  input: CreateAdapterDraftInput,
): Promise<AdapterVersion> {
  return apiRequest<AdapterVersion>(`/v1/adapters/${encodeURIComponent(adapterId)}/versions`, {
    method: "POST",
    token,
    body: {
      label: input.label,
      notes: input.notes ?? "",
    },
  });
}

export async function publishAdapterVersion(
  token: string,
  adapterId: string,
  versionId: string,
): Promise<AdapterVersion> {
  return apiRequest<AdapterVersion>(
    `/v1/adapters/${encodeURIComponent(adapterId)}/versions/${encodeURIComponent(versionId)}/publish`,
    { method: "POST", token },
  );
}
