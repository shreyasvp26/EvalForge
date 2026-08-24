import type { HTMLAttributes } from "react";

export type GlobalLoadingProps = HTMLAttributes<HTMLDivElement> & {
  label?: string;
};

/**
 * Branded boot panel for rare blocking work (session restore).
 *
 * Critical styles are inlined so a CSS/chunk load failure cannot leave users
 * on an unstyled black void. An inline failsafe clears local session markers
 * and redirects to /login if React never hydrates.
 */
export function GlobalLoading({
  label = "Loading EvalForge",
  className,
  style,
  ...props
}: GlobalLoadingProps) {
  return (
    <div
      data-ef-session-boot=""
      role="status"
      aria-live="polite"
      aria-busy
      className={className}
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 200,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "#0b0b0c",
        color: "#f2f2f3",
        fontFamily:
          'ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
        padding: 16,
        ...style,
      }}
      {...props}
    >
      <div
        style={{
          width: "100%",
          maxWidth: 280,
          display: "flex",
          flexDirection: "column",
          gap: 12,
          borderRadius: 10,
          border: "1px solid #27272a",
          background: "#111113",
          padding: 20,
          boxShadow: "0 1px 2px rgb(0 0 0 / 0.35)",
        }}
      >
        <div
          style={{
            fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
            fontSize: 12,
            letterSpacing: "0.16em",
            textTransform: "uppercase",
            color: "#f2f2f3",
          }}
        >
          EvalForge
        </div>
        <div style={{ fontSize: 12, color: "#a0a0a8" }}>Evaluation control plane</div>
        <div
          aria-hidden
          style={{ display: "flex", flexDirection: "column", gap: 8, paddingTop: 4 }}
        >
          <div style={{ height: 10, width: 112, borderRadius: 4, background: "#161618" }} />
          <div style={{ height: 8, width: "100%", borderRadius: 4, background: "#161618" }} />
          <div style={{ height: 8, width: "70%", borderRadius: 4, background: "#161618" }} />
        </div>
        <div style={{ fontSize: 12, color: "#a0a0a8" }}>{label}</div>
        <noscript>
          <p style={{ margin: "8px 0 0", fontSize: 13, lineHeight: 1.4, color: "#a0a0a8" }}>
            JavaScript is required.{" "}
            <a href="/login" style={{ color: "#c5d0db", textDecoration: "underline" }}>
              Sign in
            </a>
          </p>
        </noscript>
      </div>
      {/* Runs even if React never hydrates (chunk load failure). */}
      <script
        dangerouslySetInnerHTML={{
          __html: `(function(){try{var KEY="evalforge.auth.token",EXP="evalforge.auth.expires_at",COOKIE="evalforge.auth";function clearSession(){try{localStorage.removeItem(KEY);localStorage.removeItem(EXP);}catch(e){}try{document.cookie=COOKIE+"=; Path=/; Max-Age=0; SameSite=Lax";}catch(e){}}setTimeout(function(){var n=document.querySelector("[data-ef-session-boot]");if(!n||n.getAttribute("data-ef-stalled")==="1")return;n.setAttribute("data-ef-stalled","1");clearSession();var box=n.firstElementChild;if(box){var p=document.createElement("p");p.setAttribute("role","alert");p.style.marginTop="12px";p.style.fontSize="12px";p.style.lineHeight="1.4";p.style.color="#a0a0a8";p.innerHTML='Session could not be restored. <a href="/login" style="color:#c5d0db;text-decoration:underline">Sign in again</a>';box.appendChild(p);}setTimeout(function(){if(location.pathname==="/login")return;location.replace("/login");},1500);},4500);}catch(e){}})();`,
        }}
      />
    </div>
  );
}
