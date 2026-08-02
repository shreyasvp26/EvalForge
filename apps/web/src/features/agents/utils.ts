import type { Adapter, AdapterVersion, Agent, AgentVersion } from "@/lib/api/agents";

export function formatAgentDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function entityStatusLabel(status: string): string {
  if (status === "deprecated") return "Deprecated";
  if (status === "active") return "Active";
  return status;
}

export function entityStatusBadge(status: string): "success" | "neutral" | "warning" {
  if (status === "active") return "success";
  if (status === "deprecated") return "warning";
  return "neutral";
}

export function versionStatusLabel(status: string): string {
  if (status === "draft") return "Draft";
  if (status === "active") return "Active";
  if (status === "superseded") return "Superseded";
  if (status === "retired") return "Retired";
  return status;
}

export function versionStatusBadge(
  status: string,
): "neutral" | "success" | "warning" | "queued" | "cancelled" {
  if (status === "draft") return "queued";
  if (status === "active") return "success";
  if (status === "superseded") return "neutral";
  if (status === "retired") return "cancelled";
  return "warning";
}

export const agentsQueryKey = ["agents"] as const;

export function agentQueryKey(agentId: string) {
  return ["agents", agentId] as const;
}

export function adapterQueryKey(adapterId: string) {
  return ["adapters", adapterId] as const;
}

export function sortAgentVersionsNewestFirst(versions: AgentVersion[]): AgentVersion[] {
  return [...versions].sort((a, b) => {
    if (b.version_number !== a.version_number) {
      return b.version_number - a.version_number;
    }
    return b.created_at.localeCompare(a.created_at);
  });
}

export function sortAdapterVersionsNewestFirst(versions: AdapterVersion[]): AdapterVersion[] {
  return [...versions].sort((a, b) => {
    if (b.version_number !== a.version_number) {
      return b.version_number - a.version_number;
    }
    return b.created_at.localeCompare(a.created_at);
  });
}

export function activeAgentVersion(agent: Agent): AgentVersion | null {
  if (!agent.active_version_id) return null;
  return agent.versions.find((version) => version.id === agent.active_version_id) ?? null;
}

export function activeAdapterVersion(adapter: Adapter): AdapterVersion | null {
  if (!adapter.active_version_id) return null;
  return adapter.versions.find((version) => version.id === adapter.active_version_id) ?? null;
}
