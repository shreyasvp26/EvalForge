import { Icon } from "../../icon/icon";
import { cn } from "../../lib/cn";
import { Heading } from "../../typography/heading";
import { Text } from "../../typography/text";

import type { LucideIcon } from "lucide-react";
import type { HTMLAttributes, ReactNode } from "react";

export type EmptyStateProps = HTMLAttributes<HTMLDivElement> & {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: ReactNode;
};

export function EmptyState({
  icon,
  title,
  description,
  action,
  className,
  ...props
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-3 rounded-[var(--ef-radius-panel)] border border-dashed border-border px-6 py-12 text-center",
        className,
      )}
      {...props}
    >
      {icon ? (
        <div className="flex h-10 w-10 items-center justify-center rounded-[var(--ef-radius-control)] bg-muted text-muted-foreground">
          <Icon icon={icon} size="lg" aria-hidden />
        </div>
      ) : null}
      <Heading variant="card" level={3}>
        {title}
      </Heading>
      {description ? <Text variant="secondary">{description}</Text> : null}
      {action ? <div className="mt-2">{action}</div> : null}
    </div>
  );
}
