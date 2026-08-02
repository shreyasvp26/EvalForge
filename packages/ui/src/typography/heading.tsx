import { cva } from "class-variance-authority";

import { cn } from "../lib/cn";

import type { VariantProps } from "class-variance-authority";
import type { ElementType, HTMLAttributes, ReactNode } from "react";

const headingVariants = cva("text-foreground tracking-tight text-balance", {
  variants: {
    variant: {
      display:
        "text-[length:var(--ef-text-display)] leading-[var(--ef-text-display-leading)] font-semibold",
      page: "text-[length:var(--ef-text-page)] leading-[var(--ef-text-page-leading)] font-semibold",
      section:
        "text-[length:var(--ef-text-section)] leading-[var(--ef-text-section-leading)] font-semibold",
      card: "text-[length:var(--ef-text-card)] leading-[var(--ef-text-card-leading)] font-medium",
    },
  },
  defaultVariants: {
    variant: "page",
  },
});

const variantToLevel = {
  display: 1,
  page: 1,
  section: 2,
  card: 3,
} as const;

type HeadingVariant = NonNullable<VariantProps<typeof headingVariants>["variant"]>;

export type HeadingProps = HTMLAttributes<HTMLHeadingElement> &
  VariantProps<typeof headingVariants> & {
    level?: 1 | 2 | 3 | 4 | 5 | 6;
    children: ReactNode;
  };

export function Heading({ variant = "page", level, className, children, ...props }: HeadingProps) {
  const resolvedVariant: HeadingVariant = variant ?? "page";
  const resolvedLevel = level ?? variantToLevel[resolvedVariant];
  const Comp = `h${String(resolvedLevel)}` as ElementType;

  return (
    <Comp className={cn(headingVariants({ variant: resolvedVariant }), className)} {...props}>
      {children}
    </Comp>
  );
}
