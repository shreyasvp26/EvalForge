import { BenchmarkDetailPage } from "@/features/benchmarks/benchmark-detail-page";

export default async function ProjectBenchmarkDetailPage({
  params,
}: {
  params: Promise<{ projectId: string; suiteId: string }>;
}) {
  const { projectId, suiteId } = await params;
  return <BenchmarkDetailPage projectId={projectId} suiteId={suiteId} />;
}
