import { ChevronRight, Icon, cn } from "@agent-eval/ui";
import Link from "next/link";

export interface BreadcrumbItem {
  label: string;
  href?: string;
}

export interface BreadcrumbsProps {
  items: BreadcrumbItem[];
  className?: string;
}

/**
 * Compact breadcrumb trail for TopBar and PageHeader.
 */
export function Breadcrumbs({ items, className }: BreadcrumbsProps) {
  if (items.length === 0) return null;

  return (
    <nav aria-label="Breadcrumb" className={cn("min-w-0", className)}>
      <ol className="flex min-w-0 flex-wrap items-center gap-1">
        {items.map((item, index) => {
          const last = index === items.length - 1;
          return (
            <li key={`${item.label}-${String(index)}`} className="flex min-w-0 items-center gap-1">
              {index > 0 ? (
                <Icon
                  icon={ChevronRight}
                  size="xs"
                  className="shrink-0 text-muted-foreground"
                  aria-hidden
                />
              ) : null}
              {last || item.href === undefined ? (
                <span
                  className="truncate text-[length:var(--ef-text-caption)] font-medium text-foreground"
                  {...(last ? { "aria-current": "page" as const } : {})}
                >
                  {item.label}
                </span>
              ) : (
                <Link
                  href={item.href}
                  className="truncate text-[length:var(--ef-text-caption)] text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  {item.label}
                </Link>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
