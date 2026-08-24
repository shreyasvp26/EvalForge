"use client";

/**
 * Must not import the design system — if the UI package is what crashed,
 * depending on it here produces a blank (often black) screen.
 */
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="en">
      <body
        style={{
          margin: 0,
          minHeight: "100dvh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontFamily: "ui-sans-serif, system-ui, sans-serif",
          background: "#f7f7f8",
          color: "#111113",
        }}
      >
        <div style={{ maxWidth: 28 * 16, padding: 24 }}>
          <h1 style={{ fontSize: 20, fontWeight: 600, margin: "0 0 8px" }}>
            EvalForge could not recover
          </h1>
          <p style={{ margin: "0 0 16px", color: "#63636e", lineHeight: 1.5 }}>
            {error.message ||
              "A critical rendering error occurred. Retry to reload the application."}
          </p>
          {error.digest ? (
            <p style={{ margin: "0 0 16px", fontFamily: "ui-monospace, monospace", fontSize: 12 }}>
              Digest {error.digest}
            </p>
          ) : null}
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button
              type="button"
              onClick={reset}
              style={{
                padding: "8px 14px",
                borderRadius: 8,
                border: "none",
                background: "#3f5164",
                color: "#f7f7f8",
                cursor: "pointer",
              }}
            >
              Try again
            </button>
            <a
              href="/login"
              style={{
                padding: "8px 14px",
                borderRadius: 8,
                border: "1px solid #cfcfd6",
                background: "#fff",
                color: "#111113",
                textDecoration: "none",
              }}
            >
              Back to sign in
            </a>
          </div>
        </div>
      </body>
    </html>
  );
}
