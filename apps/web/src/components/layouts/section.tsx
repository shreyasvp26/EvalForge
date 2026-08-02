import { Heading, Stack, Text, cn } from "@agent-eval/ui";

import type { HTMLAttributes, ReactNode } from "react";

export type SectionProps = HTMLAttributes<HTMLElement> & {
  title?: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
};

/**
 * One-purpose content section with optional title row.
 */
export function Section({
  title,
  description,
  actions,
  children,
  className,
  ...props
}: SectionProps) {
  const hasHeader = title !== undefined || description !== undefined || actions !== undefined;

  return (
    <section className={cn("space-y-4", className)} data-section {...props}>
      {hasHeader ? (
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <Stack gap={1} className="min-w-0">
            {title !== undefined ? (
              <Heading variant="section" level={2}>
                {title}
              </Heading>
            ) : null}
            {description !== undefined ? <Text variant="secondary">{description}</Text> : null}
          </Stack>
          {actions !== undefined ? <div className="shrink-0">{actions}</div> : null}
        </div>
      ) : null}
      {children}
    </section>
  );
}
