/** Build-time metadata for the About page. Override via NEXT_PUBLIC_* in CI. */

export const buildInfo = {
  version: process.env["NEXT_PUBLIC_APP_VERSION"] ?? "0.0.0",
  gitCommit: process.env["NEXT_PUBLIC_GIT_COMMIT"] ?? "local",
  buildTime: process.env["NEXT_PUBLIC_BUILD_TIME"] ?? null,
  environment: process.env.NODE_ENV,
  githubUrl: "https://github.com/shreyasvp26/EvalForge",
} as const;
