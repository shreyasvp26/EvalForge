import { Icon } from "../../icon/icon";
import { Loader2 } from "../../icon/icons";
import { cn } from "../../lib/cn";

import type { IconSize } from "../../icon/icon";
import type { HTMLAttributes } from "react";

export type SpinnerProps = HTMLAttributes<HTMLSpanElement> & {
  size?: IconSize;
  label?: string;
};

export function Spinner({ size = "md", label = "Loading", className, ...props }: SpinnerProps) {
  return (
    <span
      role="status"
      className={cn("inline-flex items-center text-muted-foreground", className)}
      {...props}
    >
      <Icon icon={Loader2} size={size} className="animate-spin" aria-hidden />
      <span className="sr-only">{label}</span>
    </span>
  );
}
