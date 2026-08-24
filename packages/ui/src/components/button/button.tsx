import { Slot } from "@radix-ui/react-slot";
import { cva } from "class-variance-authority";

import { Icon } from "../../icon/icon";
import { Loader2 } from "../../icon/icons";
import { cn } from "../../lib/cn";

import type { VariantProps } from "class-variance-authority";
import type { LucideIcon } from "lucide-react";
import type { ButtonHTMLAttributes } from "react";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap font-medium transition-[background-color,color,border-color,opacity] duration-[var(--ef-duration-fast)] ease-[var(--ef-ease-standard)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-50 rounded-[var(--ef-radius-control)] text-[length:var(--ef-text-body)] leading-[var(--ef-text-body-leading)]",
  {
    variants: {
      variant: {
        // Explicit CSS vars — Tailwind `text-accent-foreground` was resolving to
        // inherited foreground (dark-on-dark) in the product theme.
        primary: "bg-[var(--ef-accent)] text-[var(--ef-accent-foreground)] hover:opacity-90",
        secondary: "bg-muted text-foreground hover:bg-border",
        outline: "border border-border bg-transparent text-foreground hover:bg-muted",
        ghost: "bg-transparent text-foreground hover:bg-muted",
        danger: "bg-[var(--ef-danger)] text-[var(--ef-danger-foreground)] hover:opacity-90",
      },
      size: {
        sm: "h-8 px-3",
        md: "h-9 px-3.5",
        lg: "h-10 px-4",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "md",
    },
  },
);

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean;
    loading?: boolean;
    leftIcon?: LucideIcon;
    rightIcon?: LucideIcon;
  };

export function Button({
  className,
  variant,
  size,
  asChild = false,
  loading = false,
  leftIcon,
  rightIcon,
  disabled,
  children,
  ...props
}: ButtonProps) {
  const isDisabled = disabled === true || loading;
  const classes = cn(buttonVariants({ variant, size }), className);

  if (asChild) {
    return (
      <Slot className={classes} {...props}>
        {children}
      </Slot>
    );
  }

  return (
    <button className={classes} disabled={isDisabled} aria-busy={loading || undefined} {...props}>
      {loading ? <Icon icon={Loader2} size="sm" className="animate-spin" aria-hidden /> : null}
      {!loading && leftIcon ? <Icon icon={leftIcon} size="sm" aria-hidden /> : null}
      {children}
      {!loading && rightIcon ? <Icon icon={rightIcon} size="sm" aria-hidden /> : null}
    </button>
  );
}

export { buttonVariants };
