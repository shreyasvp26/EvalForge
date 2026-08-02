"use client";

import { Suspense } from "react";

import { CreateRunPage } from "./create-run-page";

import { PageSkeleton } from "@/components/patterns/page-skeleton";

export function CreateRunRoute() {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <CreateRunPage />
    </Suspense>
  );
}
