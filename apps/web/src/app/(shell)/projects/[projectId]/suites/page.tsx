import { SuitesListRoute } from "@/features/suites/suites-list-route";

export default async function ProjectSuitesPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;
  return <SuitesListRoute projectId={projectId} />;
}
