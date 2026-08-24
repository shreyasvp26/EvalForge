/** Full-viewport atmospheric background for the auth landing experience. */
export function AuthLandingBackground() {
  return (
    <div aria-hidden className="pointer-events-none absolute inset-0 overflow-hidden">
      {/* Base depth */}
      <div
        className="absolute inset-0"
        style={{
          background: "var(--ef-auth-bg-depth), var(--ef-auth-bg-base)",
        }}
      />

      {/* Large indigo/violet field — upper left */}
      <div
        className="absolute -left-[20%] -top-[30%] h-[85%] w-[70%] rounded-full blur-[100px] motion-safe:animate-[ef-auth-ambient_28s_ease-in-out_infinite]"
        style={{ background: "var(--ef-auth-glow-1)" }}
      />

      {/* Purple sweep — center diagonal */}
      <div
        className="absolute left-[10%] top-[20%] h-[70%] w-[55%] rounded-full blur-[120px] motion-safe:animate-[ef-auth-sweep_36s_ease-in-out_infinite]"
        style={{ background: "var(--ef-auth-glow-2)" }}
      />

      {/* Magenta/pink accent — bottom left curve */}
      <div
        className="absolute -bottom-[25%] -left-[10%] h-[55%] w-[50%] rounded-full blur-[90px] motion-safe:animate-[ef-auth-ambient_32s_ease-in-out_infinite_reverse]"
        style={{ background: "var(--ef-auth-glow-3)" }}
      />

      {/* Soft right-side lift behind auth card */}
      <div
        className="absolute -right-[5%] top-[15%] h-[70%] w-[45%] rounded-full blur-[110px] opacity-40"
        style={{ background: "var(--ef-auth-glow-2)" }}
      />

      {/* Subtle code/telemetry texture */}
      <div
        className="absolute inset-0 opacity-[0.35]"
        style={{
          backgroundImage: `
            linear-gradient(var(--ef-auth-code-fade) 1px, transparent 1px),
            linear-gradient(90deg, var(--ef-auth-code-fade) 1px, transparent 1px)
          `,
          backgroundSize: "48px 48px",
          maskImage: "radial-gradient(ellipse 80% 70% at 30% 40%, black 0%, transparent 70%)",
        }}
      />

      {/* Vignette */}
      <div className="absolute inset-0" style={{ background: "var(--ef-auth-vignette)" }} />
    </div>
  );
}
