"use client";

import { Suspense } from "react";

import { RunListPage } from "./run-list-page";

import { PageSkeleton } from "@/components/patterns/page-skeleton";

export function RunsListRoute() {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <RunListPage />
    </Suspense>
  );
}
