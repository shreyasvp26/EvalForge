import { Text } from "@agent-eval/ui";
import Link from "next/link";

import { EvalForgeMark } from "@/components/brand/evalforge-mark";

/** EvalForge mark + wordmark for auth landing header. */
export function AuthBrandLockup({ className }: { className?: string }) {
  return (
    <Link
      href="/login"
      className={`group inline-flex items-center gap-2.5 rounded-[var(--ef-radius-control)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${className ?? ""}`}
    >
      <EvalForgeMark />
      <Text
        as="span"
        variant="caption"
        className="font-mono text-[length:var(--ef-text-body)] font-semibold uppercase tracking-[0.18em] text-foreground"
      >
        EvalForge
      </Text>
    </Link>
  );
}
