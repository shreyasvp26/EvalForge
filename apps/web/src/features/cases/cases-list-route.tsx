"use client";

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { CaseListPage } from "./case-list-page";

import { PageSkeleton } from "@/components/patterns/page-skeleton";

function CasesListWithParams({ projectId }: { projectId: string }) {
  const searchParams = useSearchParams();
  const createOpen = searchParams.get("create") === "1";
  return <CaseListPage projectId={projectId} initialCreateOpen={createOpen} />;
}

export function CasesListRoute({ projectId }: { projectId: string }) {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <CasesListWithParams projectId={projectId} />
    </Suspense>
  );
}
