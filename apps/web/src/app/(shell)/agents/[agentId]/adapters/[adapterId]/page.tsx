import { AdapterDetailPage } from "@/features/agents/adapter-detail-page";

export default async function AgentAdapterDetailRoutePage({
  params,
}: {
  params: Promise<{ agentId: string; adapterId: string }>;
}) {
  const { agentId, adapterId } = await params;
  return <AdapterDetailPage agentId={agentId} adapterId={adapterId} />;
}
