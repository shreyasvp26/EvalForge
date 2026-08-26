import type { CollectionResponse } from "@/lib/api/projects";

import { apiRequest } from "@/lib/api/client";

export interface ProviderCatalogItem {
  provider_key: string;
  display_name: string;
  status: string;
  supported_adapters: string[];
  supported_gateways: string[];
  notes: string;
  configured: boolean;
  live_capable: boolean;
  models: {
    model_id: string;
    display_name: string;
    adapter_keys: string[];
    gateway_keys: string[];
  }[];
}

export interface ModelCatalogItem {
  model_id: string;
  provider_key: string;
  display_name: string;
  adapter_keys: string[];
  gateway_keys: string[];
  notes: string;
}

export interface ProviderConnection {
  id: string;
  provider_key: string;
  credential_ref_id: string;
  display_name: string;
  status: string;
  created_at: string;
  masked_key: string;
  key_fingerprint: string;
  metadata: Record<string, string>;
}

export interface CreateProviderConnectionInput {
  provider_key: string;
  api_key: string;
  display_name?: string;
}

function buildQuery(params: Record<string, string | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === "") continue;
    search.set(key, value);
  }
  const query = search.toString();
  return query ? `?${query}` : "";
}

export async function listProviders(
  token: string,
): Promise<CollectionResponse<ProviderCatalogItem>> {
  return apiRequest<CollectionResponse<ProviderCatalogItem>>("/v1/providers", {
    method: "GET",
    token,
  });
}

export async function listModels(
  token: string,
  params?: { provider_key?: string },
): Promise<CollectionResponse<ModelCatalogItem>> {
  return apiRequest<CollectionResponse<ModelCatalogItem>>(
    `/v1/models${buildQuery({ provider_key: params?.provider_key })}`,
    { method: "GET", token },
  );
}

export async function listProviderConnections(
  token: string,
): Promise<CollectionResponse<ProviderConnection>> {
  return apiRequest<CollectionResponse<ProviderConnection>>("/v1/provider-connections", {
    method: "GET",
    token,
  });
}

export async function createProviderConnection(
  token: string,
  input: CreateProviderConnectionInput,
): Promise<ProviderConnection> {
  return apiRequest<ProviderConnection>("/v1/provider-connections", {
    method: "POST",
    token,
    body: {
      provider_key: input.provider_key,
      api_key: input.api_key,
      display_name: input.display_name ?? null,
    },
  });
}

export async function revokeProviderConnection(
  token: string,
  connectionId: string,
): Promise<ProviderConnection> {
  return apiRequest<ProviderConnection>(
    `/v1/provider-connections/${encodeURIComponent(connectionId)}`,
    { method: "DELETE", token },
  );
}

/** True when the adapter name/key maps to Google Gemini live path. */
export function isGeminiAdapterPath(adapterName: string | null | undefined): boolean {
  if (!adapterName) return false;
  const normalized = adapterName
    .trim()
    .toLowerCase()
    .replace(/[\s-]+/g, "_");
  return normalized === "gemini_cli" || normalized === "gemini" || normalized.includes("gemini");
}
