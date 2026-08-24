import { Text } from "@agent-eval/ui";
import Link from "next/link";

/** EvalForge mark + wordmark for auth landing header. */
export function AuthBrandLockup({ className }: { className?: string }) {
  return (
    <Link
      href="/login"
      className={`group inline-flex items-center gap-2.5 rounded-[var(--ef-radius-control)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${className ?? ""}`}
    >
      <span
        aria-hidden
        className="relative flex h-8 w-8 shrink-0 items-center justify-center rounded-[var(--ef-radius-control)] border border-[var(--ef-auth-feature-border)] bg-[var(--ef-auth-feature-bg)] shadow-[0_0_20px_var(--ef-auth-primary-glow)]"
      >
        <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" aria-hidden>
          <path
            d="M12 2L20 7v10l-8 5-8-5V7l8-5z"
            stroke="url(#ef-mark-gradient)"
            strokeWidth="1.5"
            strokeLinejoin="round"
          />
          <path
            d="M12 8.5v7M9 10.5l3-1.5 3 1.5"
            stroke="url(#ef-mark-gradient)"
            strokeWidth="1.25"
            strokeLinecap="round"
          />
          <defs>
            <linearGradient id="ef-mark-gradient" x1="4" y1="2" x2="20" y2="22">
              <stop stopColor="#a78bfa" />
              <stop offset="1" stopColor="#c084fc" />
            </linearGradient>
          </defs>
        </svg>
      </span>
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
