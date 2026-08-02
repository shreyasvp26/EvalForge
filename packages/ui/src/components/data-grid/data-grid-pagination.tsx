"use client";

import { Text } from "../../typography/text";
import { Button } from "../button/button";
import { Cluster } from "../layout/layout";

import type { OnChangeFn, PaginationState } from "@tanstack/react-table";

export interface DataGridPaginationProps {
  pagination: PaginationState;
  onPaginationChange: OnChangeFn<PaginationState>;
  /** Total pages. For client-side use `table.getPageCount()` from a parent controller, or compute from row count. */
  pageCount: number;
  /** Optional total filtered row count for the caption. */
  totalRows?: number;
  className?: string;
}

/**
 * Pagination controls. Client-side today; pair with `manualPagination` + `pageCount`
 * when swapping to server-driven pages later.
 */
export function DataGridPagination({
  pagination,
  onPaginationChange,
  pageCount,
  totalRows,
  className,
}: DataGridPaginationProps) {
  const pageIndex = pagination.pageIndex;
  const canPrev = pageIndex > 0;
  const canNext = pageIndex + 1 < pageCount;

  return (
    <div className={className}>
      <Cluster
        gap={3}
        className="flex-col items-stretch justify-between sm:flex-row sm:items-center"
      >
        <Text variant="caption">
          Page {String(pageIndex + 1)} of {String(Math.max(pageCount, 1))}
          {totalRows !== undefined ? ` · ${String(totalRows)} rows` : null}
        </Text>
        <Cluster gap={2} className="justify-end">
          <Button
            type="button"
            size="sm"
            variant="outline"
            disabled={!canPrev}
            onClick={() => {
              onPaginationChange((prev) => ({ ...prev, pageIndex: prev.pageIndex - 1 }));
            }}
          >
            Previous
          </Button>
          <Button
            type="button"
            size="sm"
            variant="outline"
            disabled={!canNext}
            onClick={() => {
              onPaginationChange((prev) => ({ ...prev, pageIndex: prev.pageIndex + 1 }));
            }}
          >
            Next
          </Button>
        </Cluster>
      </Cluster>
    </div>
  );
}
