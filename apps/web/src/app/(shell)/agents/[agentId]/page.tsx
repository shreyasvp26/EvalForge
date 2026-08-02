import { AgentDetailPage } from "@/features/agents/agent-detail-page";

export default async function AgentDetailRoutePage({
  params,
}: {
  params: Promise<{ agentId: string }>;
}) {
  const { agentId } = await params;
  return <AgentDetailPage agentId={agentId} />;
}
