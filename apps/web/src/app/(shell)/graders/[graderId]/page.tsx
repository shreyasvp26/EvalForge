import { GraderDetailPage } from "@/features/graders/grader-detail-page";

export default async function GraderDetailRoutePage({
  params,
}: {
  params: Promise<{ graderId: string }>;
}) {
  const { graderId } = await params;
  return <GraderDetailPage graderId={graderId} />;
}
