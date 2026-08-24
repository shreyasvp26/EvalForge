import { Skeleton, Text, cn } from "@agent-eval/ui";

import type { HTMLAttributes } from "react";

export type GlobalLoadingProps = HTMLAttributes<HTMLDivElement> & {
  label?: string;
};

/**
 * Branded boot panel for rare blocking work (session restore).
 * Includes a noscript + inline failsafe so a hydration failure cannot leave
 * users on an indefinite opaque screen.
 */
export function GlobalLoading({
  label = "Loading EvalForge",
  className,
  ...props
}: GlobalLoadingProps) {
  return (
    <div
      data-ef-session-boot=""
      className={cn(
        "fixed inset-0 z-[var(--ef-z-overlay)] flex items-center justify-center bg-background",
        className,
      )}
      role="status"
      aria-live="polite"
      aria-busy
      {...props}
    >
      <div className="flex w-64 flex-col gap-3 rounded-[var(--ef-radius-panel)] border border-border bg-card p-5 shadow-ef-sm">
        <Text
          as="div"
          variant="caption"
          className="font-mono uppercase tracking-[0.16em] text-foreground"
        >
          EvalForge
        </Text>
        <Text as="div" variant="caption" className="text-muted-foreground">
          Evaluation control plane
        </Text>
        <div className="space-y-2 pt-1" aria-hidden>
          <Skeleton className="h-2.5 w-28" />
          <Skeleton className="h-2 w-full" />
          <Skeleton className="h-2 w-[70%]" />
        </div>
        <Text variant="caption" className="text-muted-foreground">
          {label}
        </Text>
        <noscript>
          <Text as="p" variant="secondary" className="pt-2">
            JavaScript is required.{" "}
            <a href="/login" className="underline underline-offset-2">
              Sign in
            </a>
          </Text>
        </noscript>
      </div>
      {/* Runs even if React never hydrates (chunk load failure). */}
      <script
        dangerouslySetInnerHTML={{
          __html: `(function(){try{var done=false;setTimeout(function(){if(done)return;var n=document.querySelector("[data-ef-session-boot]");if(!n||n.getAttribute("data-ef-stalled")==="1")return;n.setAttribute("data-ef-stalled","1");var box=n.querySelector("div");if(!box)return;var p=document.createElement("p");p.setAttribute("role","alert");p.style.marginTop="12px";p.style.fontSize="12px";p.style.lineHeight="1.4";p.style.color="inherit";p.innerHTML="This is taking longer than expected. <a href=\\"/login\\" style=\\"text-decoration:underline\\">Sign in again</a>";box.appendChild(p);},5000);document.addEventListener("DOMContentLoaded",function(){});}catch(e){}})();`,
        }}
      />
    </div>
  );
}
