import type { CollectionResponse } from "@/lib/api/projects";

import { apiRequest } from "@/lib/api/client";

export interface PlatformVersion {
  id: string;
  platform_id: string;
  version_number: number;
  status: string;
  label: string;
  sandbox_policy: Record<string, string>;
  execution_policy: Record<string, string>;
  timeout_policy: Record<string, string>;
  environment_policy: Record<string, string>;
  grading_policy: Record<string, string>;
  notes: string;
  predecessor_version_id: string | null;
  created_at: string;
}

export interface Platform {
  id: string;
  name: string;
  status: string;
  created_at: string;
  active_version_id: string | null;
  versions: PlatformVersion[];
}

export interface ListPlatformsParams {
  cursor?: string;
  limit?: number;
  sort?: string;
}

function buildQuery(params: ListPlatformsParams): string {
  const search = new URLSearchParams();
  if (params.cursor) search.set("cursor", params.cursor);
  if (params.limit !== undefined) search.set("limit", String(params.limit));
  if (params.sort) search.set("sort", params.sort);
  const qs = search.toString();
  return qs ? `?${qs}` : "";
}

export async function listPlatforms(
  token: string,
  params: ListPlatformsParams = {},
): Promise<CollectionResponse<Platform>> {
  return apiRequest<CollectionResponse<Platform>>(`/v1/platforms${buildQuery(params)}`, {
    method: "GET",
    token,
  });
}

export async function getPlatform(token: string, platformId: string): Promise<Platform> {
  return apiRequest<Platform>(`/v1/platforms/${encodeURIComponent(platformId)}`, {
    method: "GET",
    token,
  });
}

export function pinnablePlatformVersions(platform: Platform): PlatformVersion[] {
  return platform.versions
    .filter((v) => v.status === "active" || v.status === "superseded")
    .slice()
    .sort((a, b) => b.version_number - a.version_number);
}
