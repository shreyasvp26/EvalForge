import { cva } from "class-variance-authority";

import { Icon } from "../../icon/icon";
import { AlertCircle, AlertTriangle, Check, Info } from "../../icon/icons";
import { cn } from "../../lib/cn";
import { Text } from "../../typography/text";

import type { VariantProps } from "class-variance-authority";
import type { LucideIcon } from "lucide-react";
import type { HTMLAttributes, ReactNode } from "react";

const alertVariants = cva(
  "flex gap-3 rounded-[var(--ef-radius-panel)] border px-4 py-3 text-[length:var(--ef-text-body)]",
  {
    variants: {
      variant: {
        info: "border-border bg-muted text-foreground",
        success: "border-success/30 bg-success-muted text-success",
        warning: "border-warning/30 bg-warning-muted text-warning",
        danger: "border-danger/30 bg-danger-muted text-danger",
      },
    },
    defaultVariants: {
      variant: "info",
    },
  },
);

const icons: Record<NonNullable<VariantProps<typeof alertVariants>["variant"]>, LucideIcon> = {
  info: Info,
  success: Check,
  warning: AlertTriangle,
  danger: AlertCircle,
};

export type AlertProps = HTMLAttributes<HTMLDivElement> &
  VariantProps<typeof alertVariants> & {
    title?: string;
    children: ReactNode;
  };

export function Alert({ className, variant = "info", title, children, ...props }: AlertProps) {
  const resolved = variant ?? "info";
  return (
    <div role="alert" className={cn(alertVariants({ variant: resolved }), className)} {...props}>
      <Icon icon={icons[resolved]} size="md" className="mt-0.5" aria-hidden />
      <div className="min-w-0 space-y-1">
        {title ? (
          <Text as="div" variant="body" className="font-medium text-inherit">
            {title}
          </Text>
        ) : null}
        <Text as="div" variant="secondary" className="text-inherit opacity-90">
          {children}
        </Text>
      </div>
    </div>
  );
}
