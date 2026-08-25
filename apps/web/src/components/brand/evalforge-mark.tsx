import { cn } from "@agent-eval/ui";
import Link from "next/link";

/** Shared EvalForge mark — used on auth landing and app shell. */
export function EvalForgeMark({
  className,
  size = "md",
}: {
  className?: string;
  size?: "sm" | "md";
}) {
  const box = size === "sm" ? "h-7 w-7" : "h-8 w-8";
  const icon = size === "sm" ? "h-3.5 w-3.5" : "h-4 w-4";
  const gradientId = size === "sm" ? "ef-mark-gradient-sm" : "ef-mark-gradient";

  return (
    <span
      aria-hidden
      className={cn(
        "relative flex shrink-0 items-center justify-center rounded-[var(--ef-radius-control)] border border-[var(--ef-auth-feature-border)] bg-[var(--ef-auth-feature-bg)] shadow-[0_0_16px_var(--ef-auth-primary-glow)]",
        box,
        className,
      )}
    >
      <svg viewBox="0 0 24 24" className={icon} fill="none" aria-hidden>
        <path
          d="M12 2L20 7v10l-8 5-8-5V7l8-5z"
          stroke={`url(#${gradientId})`}
          strokeWidth="1.5"
          strokeLinejoin="round"
        />
        <path
          d="M12 8.5v7M9 10.5l3-1.5 3 1.5"
          stroke={`url(#${gradientId})`}
          strokeWidth="1.25"
          strokeLinecap="round"
        />
        <defs>
          <linearGradient id={gradientId} x1="4" y1="2" x2="20" y2="22">
            <stop stopColor="#a78bfa" />
            <stop offset="1" stopColor="#c084fc" />
          </linearGradient>
        </defs>
      </svg>
    </span>
  );
}

export function EvalForgeWordmark({
  href = "/",
  className,
  showMark = true,
  subtitle,
}: {
  href?: string;
  className?: string;
  showMark?: boolean;
  subtitle?: string;
}) {
  return (
    <Link
      href={href}
      className={cn(
        "group inline-flex min-w-0 items-center gap-2.5 rounded-[var(--ef-radius-control)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        className,
      )}
    >
      {showMark ? <EvalForgeMark /> : null}
      <span className="min-w-0">
        <span className="block truncate font-mono text-[length:var(--ef-text-body)] font-semibold uppercase tracking-[0.18em] text-foreground">
          EvalForge
        </span>
        {subtitle ? (
          <span className="mt-0.5 block truncate text-[length:var(--ef-text-caption)] text-muted-foreground">
            {subtitle}
          </span>
        ) : null}
      </span>
    </Link>
  );
}
