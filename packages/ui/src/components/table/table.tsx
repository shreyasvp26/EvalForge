import { forwardRef } from "react";

import { cn } from "../../lib/cn";
import { Text } from "../../typography/text";
import { EmptyState } from "../empty-state/empty-state";
import { Spinner } from "../spinner/spinner";

import type { HTMLAttributes, ReactNode, TdHTMLAttributes, ThHTMLAttributes } from "react";

export function Table({ className, ...props }: HTMLAttributes<HTMLTableElement>) {
  return (
    <div className="relative w-full overflow-x-auto rounded-[var(--ef-radius-panel)] border border-border">
      <table className={cn("w-full caption-bottom text-left", className)} {...props} />
    </div>
  );
}

export function TableHeader({ className, ...props }: HTMLAttributes<HTMLTableSectionElement>) {
  return <thead className={cn("border-b border-border bg-muted/60", className)} {...props} />;
}

export const TableBody = forwardRef<
  HTMLTableSectionElement,
  HTMLAttributes<HTMLTableSectionElement>
>(function TableBody({ className, ...props }, ref) {
  return <tbody ref={ref} className={cn("[&_tr:last-child]:border-0", className)} {...props} />;
});

export function TableRow({ className, ...props }: HTMLAttributes<HTMLTableRowElement>) {
  return (
    <tr
      className={cn(
        "border-b border-border transition-colors duration-[var(--ef-duration-fast)] hover:bg-muted/50 focus-within:bg-muted/50 data-[state=selected]:bg-accent-muted",
        className,
      )}
      {...props}
    />
  );
}

export function TableHead({
  className,
  children,
  ...props
}: ThHTMLAttributes<HTMLTableCellElement>) {
  return (
    <th
      className={cn("h-10 px-3 text-left align-middle [&:has([role=checkbox])]:pr-0", className)}
      {...props}
    >
      {typeof children === "string" ? <Text variant="table">{children}</Text> : children}
    </th>
  );
}

export function TableCell({ className, ...props }: TdHTMLAttributes<HTMLTableCellElement>) {
  return (
    <td
      className={cn(
        "px-3 py-2.5 align-middle text-[length:var(--ef-text-body)] leading-[var(--ef-text-body-leading)] text-foreground [&:has([role=checkbox])]:pr-0",
        className,
      )}
      {...props}
    />
  );
}

export function TableCaption({ className, ...props }: HTMLAttributes<HTMLTableCaptionElement>) {
  return (
    <caption
      className={cn("mt-3 text-[length:var(--ef-text-caption)] text-muted-foreground", className)}
      {...props}
    />
  );
}

export function TableLoading({ columns = 4, rows = 5 }: { columns?: number; rows?: number }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          {Array.from({ length: columns }).map((_, i) => (
            <TableHead key={i}>
              <Text variant="table">—</Text>
            </TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {Array.from({ length: rows }).map((_, r) => (
          <TableRow key={r} aria-hidden>
            {Array.from({ length: columns }).map((_, c) => (
              <TableCell key={c}>
                <div className="h-4 w-24 animate-pulse rounded bg-muted" />
              </TableCell>
            ))}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

export function TableEmpty({
  title = "No results",
  description,
  action,
}: {
  title?: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="rounded-[var(--ef-radius-panel)] border border-border p-2">
      <EmptyState
        title={title}
        {...(description !== undefined ? { description } : {})}
        action={action}
      />
    </div>
  );
}

export function TableBusyBanner() {
  return (
    <div className="flex items-center gap-2 px-3 py-2 text-muted-foreground">
      <Spinner size="sm" />
      <Text variant="caption">Loading…</Text>
    </div>
  );
}
