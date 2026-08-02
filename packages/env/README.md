# @agent-eval/env

Typed, validated environment configuration for EvalForge Node processes.

## Why

Configuration must fail fast at startup (Backend Architecture §8). Scattering `process.env.FOO` reads makes invalid deployments fail late and inconsistently. All environment access should go through `loadEnv` (or a schema that extends `baseEnvSchema`).

## Usage

```ts
import { z } from "zod";
import { baseEnvSchema, loadEnv } from "@agent-eval/env";

const schema = baseEnvSchema.extend({
  API_PORT: z.coerce.number().int().positive().default(8000),
});

export const env = loadEnv(schema);
```

## Rules

- Do not read `process.env` outside this package (or a composition root that only calls `loadEnv`).
- Domain code must never import this package.
