# @agent-eval/logger

Structured, environment-aware logging with correlation context for EvalForge.

## Why

System Overview §12 requires structured logs and a single correlation ID from API acceptance through workers and grading. This package owns the logging **mechanism**; API and Worker entry points attach correlation / run / worker IDs. Domain code must not import this package.

## Features

- JSON logs in production; pretty transport in development
- Log levels via `LOG_LEVEL` / `createLogger({ level })`
- `childLogger` for stable module bindings
- `withLogContext` / `withLogContextAsync` for request/run correlation via `AsyncLocalStorage`
- Silent default level in `test` environment

## Usage

```ts
import { createLogger, withLogContextAsync } from "@agent-eval/logger";

const logger = createLogger({
  name: "web",
  environment: "production",
  level: "info",
});

await withLogContextAsync({ correlationId: reqId, runId }, async () => {
  logger.info({ event: "run.accepted" }, "Run accepted");
});
```
