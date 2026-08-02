"use client";

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { GraderListPage } from "./grader-list-page";

import { PageSkeleton } from "@/components/patterns/page-skeleton";

function GradersListWithParams() {
  const searchParams = useSearchParams();
  const createOpen = searchParams.get("create") === "1";
  return <GraderListPage initialCreateOpen={createOpen} />;
}

export function GradersListRoute() {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <GradersListWithParams />
    </Suspense>
  );
}
