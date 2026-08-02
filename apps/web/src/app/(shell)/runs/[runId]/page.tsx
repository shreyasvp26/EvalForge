import { RunDetailPage } from "@/features/runs/run-detail-page";

export default async function RunDetailRoutePage({
  params,
}: {
  params: Promise<{ runId: string }>;
}) {
  const { runId } = await params;
  return <RunDetailPage runId={runId} />;
}
