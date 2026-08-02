import { cva } from "class-variance-authority";

import { cn } from "../lib/cn";

import type { VariantProps } from "class-variance-authority";
import type { ElementType, HTMLAttributes, ReactNode } from "react";

const textVariants = cva("", {
  variants: {
    variant: {
      body: "text-[length:var(--ef-text-body)] leading-[var(--ef-text-body-leading)] text-foreground font-normal",
      secondary:
        "text-[length:var(--ef-text-secondary)] leading-[var(--ef-text-secondary-leading)] text-muted-foreground font-normal",
      caption:
        "text-[length:var(--ef-text-caption)] leading-[var(--ef-text-caption-leading)] text-muted-foreground font-normal",
      code: "font-mono text-[length:var(--ef-text-code)] leading-[var(--ef-text-code-leading)] text-foreground font-normal",
      table:
        "text-[length:var(--ef-text-table)] leading-[var(--ef-text-table-leading)] text-muted-foreground font-medium uppercase tracking-wide",
    },
  },
  defaultVariants: {
    variant: "body",
  },
});

const defaultElement = {
  body: "p",
  secondary: "p",
  caption: "span",
  code: "code",
  table: "span",
} as const;

type TextVariant = NonNullable<VariantProps<typeof textVariants>["variant"]>;

export type TextProps = HTMLAttributes<HTMLElement> &
  VariantProps<typeof textVariants> & {
    as?: "p" | "span" | "div" | "label" | "code" | "li";
    children: ReactNode;
  };

export function Text({ variant = "body", as, className, children, ...props }: TextProps) {
  const resolvedVariant: TextVariant = variant ?? "body";
  const Comp = (as ?? defaultElement[resolvedVariant]) as ElementType;

  return (
    <Comp className={cn(textVariants({ variant: resolvedVariant }), className)} {...props}>
      {children}
    </Comp>
  );
}
