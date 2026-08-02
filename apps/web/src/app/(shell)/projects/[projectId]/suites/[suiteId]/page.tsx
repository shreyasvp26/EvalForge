import { SuiteDetailPage } from "@/features/suites/suite-detail-page";

export default async function ProjectSuiteDetailPage({
  params,
}: {
  params: Promise<{ projectId: string; suiteId: string }>;
}) {
  const { projectId, suiteId } = await params;
  return <SuiteDetailPage projectId={projectId} suiteId={suiteId} />;
}
