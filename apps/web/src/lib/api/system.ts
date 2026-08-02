import { apiRequest, getApiBaseUrl } from "@/lib/api/client";

export interface SystemInfo {
  service: string;
  version: string;
  api_version: string;
  environment: string;
}

export interface HealthLive {
  status: string;
}

export interface HealthReady {
  status: string;
  checks: Record<string, string>;
}

export async function getSystemInfo(token: string): Promise<SystemInfo> {
  return apiRequest<SystemInfo>("/v1/system/info", { method: "GET", token });
}

/** Unauthenticated liveness probe. */
export async function getHealthLive(signal?: AbortSignal): Promise<HealthLive> {
  return apiRequest<HealthLive>("/health/live", {
    method: "GET",
    ...(signal ? { signal } : {}),
  });
}

/** Unauthenticated readiness probe. */
export async function getHealthReady(signal?: AbortSignal): Promise<HealthReady> {
  return apiRequest<HealthReady>("/health/ready", {
    method: "GET",
    ...(signal ? { signal } : {}),
  });
}

export { getApiBaseUrl };
