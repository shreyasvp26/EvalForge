"use client";

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { ProjectListPage } from "./project-list-page";

import { PageSkeleton } from "@/components/patterns/page-skeleton";

function ProjectsListWithParams() {
  const searchParams = useSearchParams();
  const createOpen = searchParams.get("create") === "1";
  return <ProjectListPage initialCreateOpen={createOpen} />;
}

export function ProjectsListRoute() {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <ProjectsListWithParams />
    </Suspense>
  );
}
