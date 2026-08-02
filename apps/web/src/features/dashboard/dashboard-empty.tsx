"use client";

import { Button, Cluster, FolderKanban, Play, Bot } from "@agent-eval/ui";
import Link from "next/link";

import { EmptyContent } from "@/components/layouts/empty-content";

export function DashboardEmpty() {
  return (
    <EmptyContent
      fill
      icon={FolderKanban}
      title="Welcome to EvalForge"
      description="Start with a project, connect an agent, then launch your first evaluation run."
      action={
        <Cluster gap={2} className="justify-center">
          <Button asChild leftIcon={FolderKanban}>
            <Link href="/projects?create=1">Create first Project</Link>
          </Button>
          <Button asChild variant="outline" leftIcon={Bot}>
            <Link href="/agents?create=1">Create first Agent</Link>
          </Button>
          <Button asChild variant="outline" leftIcon={Play}>
            <Link href="/runs/new">Launch first Run</Link>
          </Button>
        </Cluster>
      }
    />
  );
}
