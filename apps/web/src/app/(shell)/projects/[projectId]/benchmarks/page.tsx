import { BenchmarkListPage } from "@/features/benchmarks/benchmark-list-page";

export default async function ProjectBenchmarksPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;
  return <BenchmarkListPage projectId={projectId} />;
}
