import { CaseDetailPage } from "@/features/cases/case-detail-page";

export default async function ProjectCaseDetailPage({
  params,
}: {
  params: Promise<{ projectId: string; caseId: string }>;
}) {
  const { projectId, caseId } = await params;
  return <CaseDetailPage projectId={projectId} caseId={caseId} />;
}
