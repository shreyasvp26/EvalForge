import { ProjectSettingsPage } from "@/features/projects/project-settings-page";

export default async function ProjectSettingsRoute({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;
  return <ProjectSettingsPage projectId={projectId} />;
}
