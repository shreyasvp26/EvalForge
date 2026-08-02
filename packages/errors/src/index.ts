/**
 * Typed application / infrastructure / validation errors.
 *
 * Why this package exists:
 * Architecture requires distinguishing domain vs infrastructure failures and
 * never conflating them. These base types are framework-agnostic so API,
 * workers, and the future Domain layer can share one vocabulary without
 * depending on HTTP or ORM details.
 */

export type ErrorDetails = Readonly<Record<string, unknown>>;

export interface SerializedError {
  readonly name: string;
  readonly code: string;
  readonly message: string;
  readonly retryable: boolean;
  readonly details?: ErrorDetails;
  readonly cause?: SerializedError | undefined;
}

export interface AppErrorOptions {
  readonly message: string;
  readonly code: string;
  readonly cause?: unknown;
  readonly details?: ErrorDetails;
  readonly retryable?: boolean;
}

function serializeCause(cause: unknown): SerializedError | undefined {
  if (cause instanceof AppError) {
    return cause.toJSON();
  }
  if (cause instanceof Error) {
    return {
      name: cause.name,
      code: "UNTYPED_ERROR",
      message: cause.message,
      retryable: false,
    };
  }
  return undefined;
}

/**
 * Root error type for EvalForge. Prefer subclasses over throwing this directly.
 */
export abstract class AppError extends Error {
  readonly code: string;
  readonly details: ErrorDetails | undefined;
  readonly retryable: boolean;
  override readonly cause: unknown;

  protected constructor(options: AppErrorOptions) {
    super(options.message, options.cause === undefined ? undefined : { cause: options.cause });
    this.name = new.target.name;
    this.code = options.code;
    this.details = options.details;
    this.retryable = options.retryable ?? false;
    this.cause = options.cause;
    Object.setPrototypeOf(this, new.target.prototype);
  }

  toJSON(): SerializedError {
    return {
      name: this.name,
      code: this.code,
      message: this.message,
      retryable: this.retryable,
      ...(this.details === undefined ? {} : { details: this.details }),
      ...(serializeCause(this.cause) === undefined ? {} : { cause: serializeCause(this.cause) }),
    };
  }
}

/**
 * Expected application/use-case failure (authorization, invalid state for an
 * operation). Not retryable by default.
 */
export class ApplicationError extends AppError {
  constructor(options: AppErrorOptions) {
    super({ ...options, retryable: options.retryable ?? false });
  }
}

/**
 * Infrastructure failure (database, queue, object storage, network).
 * Mark `retryable: true` for transient failures.
 */
export class InfrastructureError extends AppError {
  constructor(options: AppErrorOptions) {
    super({ ...options, retryable: options.retryable ?? false });
  }
}

/**
 * Input or configuration validation failure. Never retryable.
 */
export class ValidationError extends AppError {
  constructor(options: Omit<AppErrorOptions, "retryable">) {
    super({ ...options, retryable: false });
  }
}

/**
 * Invalid or missing environment/configuration at startup. Fail fast.
 */
export class ConfigurationError extends AppError {
  constructor(options: Omit<AppErrorOptions, "retryable">) {
    super({ ...options, retryable: false });
  }
}

export function isAppError(value: unknown): value is AppError {
  return value instanceof AppError;
}

export function serializeError(error: unknown): SerializedError {
  if (error instanceof AppError) {
    return error.toJSON();
  }
  if (error instanceof Error) {
    return {
      name: error.name,
      code: "UNTYPED_ERROR",
      message: error.message,
      retryable: false,
    };
  }
  return {
    name: "UnknownError",
    code: "UNKNOWN",
    message: typeof error === "string" ? error : "Unknown error",
    retryable: false,
  };
}
