/**
 * Cross-cutting utilities with no business meaning.
 * Keep this package small — prefer domain-local helpers over dumping here.
 */

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

/**
 * Exhaustiveness check for switch/if narrowing. Compile-time + runtime guard.
 */
export function assertNever(value: never, message = "Unexpected value"): never {
  throw new Error(`${message}: ${JSON.stringify(value)}`);
}

/**
 * Runtime assertion for invariants that must hold. Prefer typed errors at
 * boundaries; use this for programmer mistakes inside a module.
 */
export function invariant(condition: unknown, message = "Invariant violated"): asserts condition {
  if (!condition) {
    throw new Error(message);
  }
}

export function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

export function isUuid(value: unknown): value is string {
  return typeof value === "string" && UUID_RE.test(value);
}

/**
 * Correlation / request identifiers. Uses crypto.randomUUID for portability
 * across Node, browsers, and workers without extra dependencies.
 */
export function createCorrelationId(): string {
  return crypto.randomUUID();
}

export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}
