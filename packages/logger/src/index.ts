import { AsyncLocalStorage } from "node:async_hooks";

import { createCorrelationId } from "@agent-eval/utils";
import pino from "pino";

import type { LogLevel } from "@agent-eval/env";
import type { Logger as PinoLogger } from "pino";

/**
 * Structured logging with correlation context.
 *
 * Why: System Overview §12 — structured logs + correlation IDs threaded from
 * API/Worker entry points. This package provides the mechanism; entry points
 * attach context. Domain code must not depend on logging.
 */

export type LogContext = Readonly<{
  correlationId?: string;
  runId?: string;
  workerId?: string;
  [key: string]: string | number | boolean | undefined;
}>;

export type Logger = PinoLogger;

export interface CreateLoggerOptions {
  readonly name?: string;
  readonly level?: LogLevel;
  readonly environment?: "development" | "test" | "production";
  /** Extra bindings applied to every log line from this logger. */
  readonly bindings?: LogContext;
}

const contextStorage = new AsyncLocalStorage<LogContext>();

function resolveLevel(
  level: LogLevel | undefined,
  environment: CreateLoggerOptions["environment"],
): LogLevel {
  if (level !== undefined) {
    return level;
  }
  if (environment === "test") {
    return "silent";
  }
  if (environment === "production") {
    return "info";
  }
  return "debug";
}

/**
 * Create a process-level logger. Prefer one root logger per process, then
 * `child()` for module/component bindings.
 */
export function createLogger(options: CreateLoggerOptions = {}): Logger {
  const environment = options.environment ?? "development";
  const level = resolveLevel(options.level, environment);
  const isProduction = environment === "production";

  const base = pino({
    name: options.name ?? "evalforge",
    level,
    base: {
      service: options.name ?? "evalforge",
      ...options.bindings,
    },
    timestamp: pino.stdTimeFunctions.isoTime,
    formatters: {
      level(label) {
        return { level: label };
      },
    },
    ...(isProduction
      ? {}
      : {
          transport: {
            target: "pino-pretty",
            options: {
              colorize: true,
              translateTime: "SYS:standard",
              ignore: "pid,hostname",
            },
          },
        }),
    mixin() {
      return { ...contextStorage.getStore() };
    },
  });

  return base;
}

/** Read the async correlation context for the current execution, if any. */
export function getLogContext(): LogContext | undefined {
  return contextStorage.getStore();
}

/**
 * Run `fn` with correlation fields attached to every log line emitted inside.
 * Generates a correlation ID when the caller does not supply one.
 */
export function withLogContext<T>(context: LogContext, fn: () => T): T {
  const current = contextStorage.getStore();
  const next: LogContext = {
    ...current,
    ...context,
    correlationId: context.correlationId ?? current?.correlationId ?? createCorrelationId(),
  };
  return contextStorage.run(next, fn);
}

export async function withLogContextAsync<T>(
  context: LogContext,
  fn: () => Promise<T>,
): Promise<T> {
  const current = contextStorage.getStore();
  const next: LogContext = {
    ...current,
    ...context,
    correlationId: context.correlationId ?? current?.correlationId ?? createCorrelationId(),
  };
  return contextStorage.run(next, fn);
}

/** Convenience: bind a child logger with static fields (module name, etc.). */
export function childLogger(logger: Logger, bindings: LogContext): Logger {
  return logger.child(bindings);
}
