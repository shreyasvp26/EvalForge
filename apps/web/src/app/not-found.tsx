import { Button } from "@agent-eval/ui";
import Link from "next/link";

import { NotFoundState } from "@/components/patterns/not-found-state";

export default function NotFound() {
  return (
    <div className="mx-auto flex min-h-dvh max-w-lg items-center px-6 py-16">
      <NotFoundState
        resourceLabel="page"
        title="Page not found"
        description="That route is not part of EvalForge — or the URL is wrong."
        action={
          <div className="flex flex-wrap justify-center gap-2">
            <Button asChild>
              <Link href="/">Back to Overview</Link>
            </Button>
            <Button asChild variant="outline">
              <Link href="/projects">Open Projects</Link>
            </Button>
          </div>
        }
      />
    </div>
  );
}
