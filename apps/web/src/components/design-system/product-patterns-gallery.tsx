"use client";

import { Button, Input, Stack, Text } from "@agent-eval/ui";
import { useState } from "react";

import {
  ComingSoonState,
  ConfirmationDialog,
  FormSkeleton,
  InlineError,
  NoResultsState,
  NotFoundState,
  PageSkeleton,
  PermissionDeniedState,
  SearchEmptyState,
  SuccessState,
  TableSkeleton,
} from "@/components/patterns";

export function ProductPatternsGallery() {
  const [confirmOpen, setConfirmOpen] = useState(false);

  return (
    <Stack gap={8}>
      <Stack gap={2}>
        <Text variant="caption" className="font-mono uppercase tracking-wide">
          When to use
        </Text>
        <ul className="list-disc space-y-2 pl-5 text-[length:var(--ef-text-body)] text-muted-foreground">
          <li>
            <strong className="font-medium text-foreground">Skeletons</strong> for route and table
            loads — preserve layout; avoid centered spinners.
          </li>
          <li>
            <strong className="font-medium text-foreground">SearchEmpty / NoResults</strong> when a
            query or filter excludes everything (not first-time empty).
          </li>
          <li>
            <strong className="font-medium text-foreground">ConfirmationDialog</strong> for
            destructive or irreversible actions; support async confirm + loading.
          </li>
          <li>
            <strong className="font-medium text-foreground">InlineError</strong> for
            field/validation; page-level ErrorContent / ErrorBoundary for harder failures.
          </li>
        </ul>
      </Stack>

      <div className="grid gap-6 lg:grid-cols-2">
        <Stack gap={2}>
          <Text variant="table">PageSkeleton</Text>
          <PageSkeleton />
        </Stack>
        <Stack gap={2}>
          <Text variant="table">TableSkeleton</Text>
          <TableSkeleton rows={4} columns={3} />
        </Stack>
      </div>

      <Stack gap={2}>
        <Text variant="table">FormSkeleton</Text>
        <FormSkeleton fields={3} />
      </Stack>

      <div className="grid gap-4 md:grid-cols-2">
        <SearchEmptyState
          query="xyzzy"
          action={
            <Button size="sm" variant="outline">
              Clear search
            </Button>
          }
        />
        <NoResultsState
          action={
            <Button size="sm" variant="outline">
              Clear filters
            </Button>
          }
        />
        <NotFoundState
          resourceLabel="item"
          action={
            <Button size="sm" variant="secondary">
              Back to list
            </Button>
          }
        />
        <PermissionDeniedState
          action={
            <Button size="sm" variant="secondary">
              Switch project
            </Button>
          }
        />
        <ComingSoonState featureLabel="Comparisons" />
        <SuccessState action={<Button size="sm">Continue</Button>} />
      </div>

      <Stack gap={3}>
        <Text variant="table">InlineError</Text>
        <Stack gap={2} className="max-w-sm">
          <Input aria-invalid aria-label="Example" placeholder="Required field" />
          <InlineError>Enter a value to continue.</InlineError>
        </Stack>
        <InlineError density="block" title="Couldn’t save">
          Retry when the connection is stable.
        </InlineError>
      </Stack>

      <Stack gap={2}>
        <Text variant="table">ConfirmationDialog</Text>
        <div>
          <Button
            variant="danger"
            size="sm"
            onClick={() => {
              setConfirmOpen(true);
            }}
          >
            Delete sample
          </Button>
        </div>
        <ConfirmationDialog
          open={confirmOpen}
          onOpenChange={setConfirmOpen}
          variant="destructive"
          title="Delete this sample?"
          description="This demonstration can’t be undone. In product flows, describe what is lost and what remains."
          confirmLabel="Delete"
          onConfirm={async () => {
            await new Promise((resolve) => {
              setTimeout(resolve, 500);
            });
          }}
        />
      </Stack>
    </Stack>
  );
}
