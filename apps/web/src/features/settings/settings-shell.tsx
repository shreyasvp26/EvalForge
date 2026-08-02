"use client";

import { SettingsNav } from "./settings-nav";

import type { ReactNode } from "react";

import { PageHeader } from "@/components/layouts/page-header";
import { PageLayout } from "@/components/layouts/page-layout";
import { Breadcrumbs } from "@/components/shell/breadcrumbs";

export function SettingsShell({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: ReactNode;
}) {
  return (
    <PageLayout width="lg">
      <PageHeader
        breadcrumbs={
          <Breadcrumbs
            items={[
              { label: "Workspace", href: "/" },
              { label: "Settings", href: "/settings" },
              { label: title },
            ]}
          />
        }
        eyebrow="Administration"
        title={title}
        description={description}
      />
      <div className="mt-8 grid gap-8 md:grid-cols-[11rem_minmax(0,1fr)]">
        <SettingsNav />
        <div className="min-w-0 space-y-6">{children}</div>
      </div>
    </PageLayout>
  );
}
