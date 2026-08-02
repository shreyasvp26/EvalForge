import { ConfigurationError } from "@agent-eval/errors";
import { z } from "zod";

/**
 * Typed environment loading with fail-fast validation.
 *
 * Why: Backend Architecture §8 — configuration is a dedicated, framework-
 * agnostic surface. Callers must not read `process.env` directly outside this
 * package (or a thin composition root that calls `loadEnv`).
 */

export const nodeEnvSchema = z.enum(["development", "test", "production"]);

export const logLevelSchema = z.enum([
  "fatal",
  "error",
  "warn",
  "info",
  "debug",
  "trace",
  "silent",
]);

/**
 * Baseline env shared by all Node processes (API gateway side, workers tooling,
 * scripts). Service-specific packages should extend this schema.
 */
export const baseEnvSchema = z.object({
  NODE_ENV: nodeEnvSchema.default("development"),
  LOG_LEVEL: logLevelSchema.default("info"),
});

export type BaseEnv = z.infer<typeof baseEnvSchema>;
export type NodeEnv = z.infer<typeof nodeEnvSchema>;
export type LogLevel = z.infer<typeof logLevelSchema>;

export type EnvSource = Record<string, string | undefined>;

export interface LoadEnvOptions {
  /** Defaults to `process.env`. Injected in tests. */
  readonly source?: EnvSource;
}

function formatZodError(error: z.ZodError): string {
  return error.issues
    .map((issue) => {
      const path = issue.path.length > 0 ? issue.path.join(".") : "(root)";
      return `${path}: ${issue.message}`;
    })
    .join("; ");
}

/**
 * Parse and validate environment variables. Throws `ConfigurationError` on
 * failure so processes exit before serving traffic with invalid config.
 */
export function loadEnv<TSchema extends z.ZodTypeAny>(
  schema: TSchema,
  options: LoadEnvOptions = {},
): z.infer<TSchema> {
  const source = options.source ?? process.env;
  const result = schema.safeParse(source);

  if (!result.success) {
    throw new ConfigurationError({
      code: "INVALID_CONFIGURATION",
      message: `Invalid configuration: ${formatZodError(result.error)}`,
      details: { issues: result.error.issues },
    });
  }

  return result.data as z.infer<TSchema>;
}

/** Convenience loader for the shared baseline schema. */
export function loadBaseEnv(options?: LoadEnvOptions): BaseEnv {
  return loadEnv(baseEnvSchema, options);
}
