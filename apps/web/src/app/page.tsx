export default function HomePage() {
  return (
    <main className="mx-auto flex min-h-full max-w-3xl flex-col justify-center gap-4 px-6 py-16">
      <p className="font-mono text-sm text-muted-foreground">EvalForge</p>
      <h1 className="text-3xl font-semibold tracking-tight text-foreground">Frontend foundation</h1>
      <p className="max-w-prose text-muted-foreground">
        Phase 15A bootstrap. The design system, app shell, and galleries land in subsequent
        milestones. Product CRUD is intentionally out of scope.
      </p>
    </main>
  );
}
