import { Suspense } from "react";

import { PageLayout } from "@/components/layouts/page-layout";
import { DetailSkeleton } from "@/components/patterns/detail-skeleton";
import { BenchmarkExecutionPage } from "@/features/benchmarks/benchmark-execution-page";

export default async function ProjectBenchmarkExecutionPage({
  params,
}: {
  params: Promise<{ projectId: string; suiteId: string; executionGroupId: string }>;
}) {
  const { projectId, suiteId, executionGroupId } = await params;
  return (
    <Suspense
      fallback={
        <PageLayout>
          <DetailSkeleton withInspector={false} />
        </PageLayout>
      }
    >
      <BenchmarkExecutionPage
        projectId={projectId}
        suiteId={suiteId}
        executionGroupId={executionGroupId}
      />
    </Suspense>
  );
}
