import { CasesListRoute } from "@/features/cases/cases-list-route";

export default async function ProjectCasesPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;
  return <CasesListRoute projectId={projectId} />;
}
