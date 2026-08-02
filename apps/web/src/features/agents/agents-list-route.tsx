"use client";

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { AgentListPage } from "./agent-list-page";

import { PageSkeleton } from "@/components/patterns/page-skeleton";

function AgentsListWithParams() {
  const searchParams = useSearchParams();
  const createOpen = searchParams.get("create") === "1";
  return <AgentListPage initialCreateOpen={createOpen} />;
}

export function AgentsListRoute() {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <AgentsListWithParams />
    </Suspense>
  );
}
