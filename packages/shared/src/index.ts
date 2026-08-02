/**
 * Convenience barrel for EvalForge TypeScript foundation packages.
 *
 * Prefer importing from the specific package (`@agent-eval/logger`, etc.) in
 * new code. This barrel exists for gradual adoption and mirrors the mental
 * model of the Python `shared/` package.
 */

export {
  AppError,
  ApplicationError,
  ConfigurationError,
  InfrastructureError,
  ValidationError,
  isAppError,
  serializeError,
} from "@agent-eval/errors";
export type { AppErrorOptions, ErrorDetails, SerializedError } from "@agent-eval/errors";

export {
  baseEnvSchema,
  loadBaseEnv,
  loadEnv,
  logLevelSchema,
  nodeEnvSchema,
} from "@agent-eval/env";
export type { BaseEnv, EnvSource, LoadEnvOptions, LogLevel, NodeEnv } from "@agent-eval/env";

export {
  childLogger,
  createLogger,
  getLogContext,
  withLogContext,
  withLogContextAsync,
} from "@agent-eval/logger";
export type { CreateLoggerOptions, LogContext, Logger } from "@agent-eval/logger";

export {
  assertNever,
  createCorrelationId,
  invariant,
  isNonEmptyString,
  isUuid,
  sleep,
} from "@agent-eval/utils";
