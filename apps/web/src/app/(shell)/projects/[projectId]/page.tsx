import { ProjectDetailPage } from "@/features/projects/project-detail-page";

export default async function ProjectPage({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = await params;
  return <ProjectDetailPage projectId={projectId} />;
}
