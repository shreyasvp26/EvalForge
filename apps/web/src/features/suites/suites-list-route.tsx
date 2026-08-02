"use client";

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { SuiteListPage } from "./suite-list-page";

import { PageSkeleton } from "@/components/patterns/page-skeleton";

function SuitesListWithParams({ projectId }: { projectId: string }) {
  const searchParams = useSearchParams();
  const createOpen = searchParams.get("create") === "1";
  return <SuiteListPage projectId={projectId} initialCreateOpen={createOpen} />;
}

export function SuitesListRoute({ projectId }: { projectId: string }) {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <SuitesListWithParams projectId={projectId} />
    </Suspense>
  );
}
