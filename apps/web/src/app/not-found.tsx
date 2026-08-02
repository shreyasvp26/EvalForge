import { Button } from "@agent-eval/ui";
import Link from "next/link";

import { NotFoundState } from "@/components/patterns/not-found-state";

export default function NotFound() {
  return (
    <div className="mx-auto flex min-h-dvh max-w-lg items-center px-6 py-16">
      <NotFoundState
        resourceLabel="page"
        title="Page not found"
        description="That route is not part of the EvalForge shell yet — or the URL is wrong."
        action={
          <Button asChild variant="secondary">
            <Link href="/">Back to projects</Link>
          </Button>
        }
      />
    </div>
  );
}
